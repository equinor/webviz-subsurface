import logging
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pandas as pd
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_store import webvizstore

import webviz_subsurface
from webviz_subsurface._models import InplaceVolumesModel
from webviz_subsurface._models.inplace_volumes_model import (
    extract_volframe_from_tableprovider,
)
from webviz_subsurface._providers import EnsembleTableProviderFactory
from webviz_subsurface._utils.ensemble_table_provider_set_factory import (
    create_parameter_providerset_from_paths,
)

from .controllers import (
    comparison_controllers,
    distribution_controllers,
    export_data_controllers,
    fipfile_qc_controller,
    layout_controllers,
    selections_controllers,
    tornado_controllers,
)
from .views import clientside_stores, main_view
from .volume_validator_and_combinator import VolumeValidatorAndCombinator

LOGGER = logging.getLogger(__name__)


class VolumetricAnalysis(WebvizPluginABC):
    """Dashboard to analyze volumetrics results from FMU ensembles, both monte carlo
and sensitivity runs are supported.

This dashboard is built with static volumetric data in mind. However both static and dynamic
volumefiles are supported as input, and the type is determined by an automatic check. To be
defined as a static source the standard FMU-format of such files must be followed.
[see FMU wiki for decription of volumetric standards](https://wiki.equinor.com/wiki/index.php/\
FMU_standards/Volumetrics)

The dashboard can be used as a tool to compare dynamic and static volumes.
This is done by creating sets of FIPNUM's and REGION∕ZONE's that are comparable
in volumes, and combining volumes per set. To trigger this behaviour a
fipfile with FIPNUM to REGION∕ZONE mapping information must be provided. Different formats
of this fipfile are supported [examples can be seen here](https://fmu-docs.equinor.com/docs/\
subscript/scripts/rmsecl_volumetrics.html#example).

The plugin behavoiur is dependent on the input files and their type (static/dynamic):
* If the input file(s) are static, different input preparations are triggered to enhance the
  analysis:
    * The fluid type is determined by the column name suffixes, either (_OIL or _GAS). This suffix
      is removed and a `FLUID_ZONE` column is added to be used as a filter or selector.
    * If total geometric volumes are included (suffix _TOTAL) they will be used to compute volumes
      from the water zone and "water" will be added to the `FLUID_ZONE` column.
    * Property columns (e.g. PORO, SW) are automatically computed from the data as long as
      relevant volumetric columns are present. NET volume and NTG can be computed from a FACIES
      column by defining which facies are non-net.
* If the input file(s) are dynamic these operations are skipped.

!> Be aware that if more than one source is given as input, only common columns between the sources
   are kept. Hence it is often preferrable to initialize the plugin multiple times dependent on the
   analysis task in question. E.g. a pure static input will allow for a detailed analysis of
   volumetric data due to the input preparations mentioned above. While a mix of both static and
   dynamic data will limit the available columns but enable comparison of these data on a
   comparable level.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).

---

**Using aggregated data**
* **`csvfile_vol`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns \
(absolute path or relative to config file).
* **`csvfile_parameters`:** Aggregated csvfile with parameter data (absolute path or \
relative to config file).`REAL` and `ENSEMBLE` are mandatory columns.


**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.


**Common settings**
* **`drop_failed_realizations`:** Option to drop or include failed realizations.
    The success criteria is based on the presence of an 'OK' file in the realization runpath.
* **`non_net_facies`:** List of facies which are non-net.
* **`fipfile`:** Path to a yaml-file that defines a match between FIPNUM regions
    and human readable regions, zones and etc to be used as filters.
* **`colors`:** List of hex colors use.
---

?> The input files must follow FMU standards.


The input files are given to the plugin in the 'volfiles' argument. This is a dictionary
where the key will used in the SOURCE column and the value is the name of a volumetric file,
or a list of volumetric files belonging to the specific data source (e.g. geogrid).
If users have multiple csv-files from one data source e.g. geogrid_oil.csv and geogrid_gas.csv,
it is recommended to put these into a list of files for the source geogrid as such:

```yaml
volfiles:
    geogrid:
        - geogrid_oil.csv
        - geogrid_gas.csv
```

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/reek_test_data/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/\
realization-0/iter-0/share/results/volumes/geogrid--vol.csv).

For sensitivity runs the sensitivity information is extracted automatically if `ensembles`\
is given as input, as long as `SENSCASE` and `SENSNAME` are found in `parameters.txt`.\
* [Example of an aggregated file to use with `csvfile_parameters`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_test_data/aggregated_data/parameters.csv)


**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `FIPNUM`
* `SET`
* `LICENSE`
* `SOURCE`
* `SENSNAME`
* `SENSCASE`


**Remaining columns are seen as volumetric responses.** """

    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile_vol: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        non_net_facies: Optional[List[str]] = None,
        fipfile: Path = None,
        drop_failed_realizations: bool = True,
        colors: List[str] = None,
    ):
        super().__init__()
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "inplace_volumes.css"
        )

        self.fipfile = fipfile
        parameters: Optional[pd.DataFrame] = None

        LOGGER.warning(
            f" Plugin argument drop_failed_realizations is set to {drop_failed_realizations}. "
            "An 'OK' file in the realization runpath is used as success criteria"
        )
        self.colors = (
            colors
            if colors is not None
            else [
                "#1F77B4",
                "#FF7F0E",
                "#2CA02C",
                "#D62728",
                "#9467BD",
                "#8C564B",
                "#E377C2",
                "#7F7F7F",
                "#BCBD22",
                "#17BECF",
                "#FD3216",
                "#00FE35",
                "#6A76FC",
                "#FED4C4",
                "#FE00CE",
                "#0DF9FF",
                "#F6F926",
                "#FF9616",
                "#479B55",
                "#EEA6FB",
                "#DC587D",
                "#D626FF",
                "#6E899C",
                "#00B5F7",
                "#B68E00",
                "#C9FBE5",
                "#FF0092",
                "#22FFA7",
                "#E3EE9E",
                "#86CE00",
                "#BC7196",
                "#7E7DCD",
                "#FC6955",
                "#E48F72",
            ]
        )
        if csvfile_vol:
            table_provider = EnsembleTableProviderFactory.instance()
            volumes_table = table_provider.create_from_ensemble_csv_file(csvfile_vol)
            if csvfile_parameters:
                parameters = table_provider.create_from_ensemble_csv_file(
                    csvfile_parameters
                )

        elif ensembles and volfiles:
            ensemble_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            volumes_table = extract_volframe_from_tableprovider(
                ensemble_paths, volfolder, volfiles, drop_failed_realizations
            )
            parameter_provider_set = create_parameter_providerset_from_paths(
                ensemble_paths, drop_failed_realizations
            )
            parameters = parameter_provider_set.get_aggregated_dataframe()
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" or "ensembles" and "volfiles"'
            )

        vcomb = VolumeValidatorAndCombinator(
            volumes_table=volumes_table,
            fipfile=get_path(self.fipfile) if self.fipfile else None,
        )
        if self.fipfile and vcomb.dframe.empty:
            raise ValueError(
                "Not possible to obtain any results using the provided fipfile."
            )
        self.disjoint_set_df = vcomb.disjoint_set_df
        self.volmodel = InplaceVolumesModel(
            volumes_table=vcomb.dframe,
            parameter_table=parameters,
            non_net_facies=non_net_facies,
            volume_type=vcomb.volume_type,
        )
        self.theme = webviz_settings.theme
        self.set_callbacks()

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                clientside_stores(get_uuid=self.uuid),
                main_view(
                    get_uuid=self.uuid,
                    volumemodel=self.volmodel,
                    disjoint_set_df=self.disjoint_set_df,
                ),
            ],
        )

    def set_callbacks(self) -> None:
        selections_controllers(get_uuid=self.uuid, volumemodel=self.volmodel)
        distribution_controllers(
            get_uuid=self.uuid, volumemodel=self.volmodel, colors=self.colors
        )
        tornado_controllers(
            get_uuid=self.uuid, volumemodel=self.volmodel, theme=self.theme
        )
        comparison_controllers(get_uuid=self.uuid, volumemodel=self.volmodel)
        layout_controllers(get_uuid=self.uuid)
        export_data_controllers(get_uuid=self.uuid)
        fipfile_qc_controller(get_uuid=self.uuid, disjoint_set_df=self.disjoint_set_df)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        if self.fipfile is not None:
            return [(get_path, [{"path": self.fipfile}])]
        return []


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)
