from pathlib import Path
from typing import Callable, List, Optional, Tuple

import pandas as pd
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_store import webvizstore

import webviz_subsurface
from webviz_subsurface._models import (
    EnsembleSetModel,
    InplaceVolumesModel,
    caching_ensemble_set_model_factory,
)
from webviz_subsurface._models.inplace_volumes_model import extract_volumes

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
* **`non_net_facies`:** List of facies which are non-net.
* **`fipfile`:** Path to a yaml-file that defines a match between FIPNUM regions
    and human readable regions, zones and etc to be used as filters.
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

    # pylint: disable=too-many-arguments
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
    ):
        super().__init__()
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "inplace_volumes.css"
        )

        self.csvfile_vol = csvfile_vol
        self.csvfile_parameters = csvfile_parameters
        self.fipfile = fipfile

        if csvfile_vol:
            volumes_table = read_csv(csvfile_vol)
            parameters: Optional[pd.DataFrame] = (
                read_csv(csvfile_parameters) if csvfile_parameters else None
            )

        elif ensembles and volfiles:
            ensemble_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths=ensemble_paths,
                )
            )
            parameters = self.emodel.load_parameters()
            volumes_table = extract_volumes(self.emodel, volfolder, volfiles)

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" or "ensembles" and "volfiles"'
            )

        vcomb = VolumeValidatorAndCombinator(
            volumes_table=volumes_table,
            fipfile=get_path(self.fipfile) if self.fipfile else None,
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
                    theme=self.theme,
                    disjoint_set_df=self.disjoint_set_df,
                ),
            ],
        )

    def set_callbacks(self) -> None:
        selections_controllers(get_uuid=self.uuid, volumemodel=self.volmodel)
        distribution_controllers(get_uuid=self.uuid, volumemodel=self.volmodel)
        tornado_controllers(
            get_uuid=self.uuid, volumemodel=self.volmodel, theme=self.theme
        )
        comparison_controllers(get_uuid=self.uuid, volumemodel=self.volmodel)
        layout_controllers(get_uuid=self.uuid)
        export_data_controllers(get_uuid=self.uuid)
        fipfile_qc_controller(get_uuid=self.uuid, disjoint_set_df=self.disjoint_set_df)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions = []
        if self.csvfile_vol is not None:
            store_functions.append((read_csv, [{"csv_file": self.csvfile_vol}]))
        else:
            store_functions.extend(self.emodel.webvizstore)
        if self.fipfile is not None:
            store_functions.append((get_path, [{"path": self.fipfile}]))
        if self.csvfile_parameters is not None:
            store_functions.append((read_csv, [{"csv_file": self.csvfile_parameters}]))
        return store_functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file)


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)
