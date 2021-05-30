from typing import List, Tuple, Callable, Optional
from pathlib import Path
import pandas as pd
import dash
import dash_html_components as html
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface

from webviz_subsurface._models import EnsembleSetModel, InplaceVolumesModel
from webviz_subsurface._models import caching_ensemble_set_model_factory
from webviz_subsurface._models.inplace_volumes_model import extract_volumes

from .views import clientside_stores, main_view
from .controllers import (
    distribution_controllers,
    selections_controllers,
    layout_controllers,
)


class VolumetricAnalysis(WebvizPluginABC):
    """Dashboard to analyze volumetrics results from
FMU ensembles.

This plugin supports both monte carlo and sensitivity runs, and will automatically detect
which case has been run.

The fluid type is determined by the column name suffixes, either (_OIL or _GAS). This suffix
is removed and a `FLUID` column is added to be used as a filter or selector.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).

---

**Using aggregated data**
* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns \
(absolute path or relative to config file).

**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.

---

?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/\
realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

For sensitivity runs the sensitivity information is extracted automatically if `ensembles`\
is given as input, as long as `SENSCASE` and `SENSNAME` is found in `parameters.txt`.\
* [Example of an aggregated file to use with `csvfile_parameters`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
aggregated_data/parameters.csv)


**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)
* `SENSNAME`
* `SENSCASE`


**Remaining columns are seen as volumetric responses.** """

    # pylint: disable=too-many-arguments, too-many-instance-attributes, too-many-locals
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile_vol: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        drop_constants: bool = True,
    ):

        super().__init__()

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "container.css"
        )
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "inplace_volumes.css"
        )
        self.csvfile_vol = csvfile_vol
        self.csvfile_parameters = csvfile_parameters
        self.volfiles = volfiles
        self.volfolder = volfolder

        if csvfile_vol and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile_vol:
            volume_table = read_csv(csvfile_vol)
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

            volume_table = extract_volumes(self.emodel, volfolder, volfiles)

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )

        self.volmodel = InplaceVolumesModel(volume_table, parameters, drop_constants)
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    #    @property
    #    def tour_steps(self) -> List[Dict]:
    #        return generate_tour_steps(get_uuid=self.uuid)

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                clientside_stores(get_uuid=self.uuid),
                main_view(
                    get_uuid=self.uuid,
                    volumemodel=self.volmodel,
                    theme=self.theme,
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        selections_controllers(app=app, get_uuid=self.uuid, volumemodel=self.volmodel)
        distribution_controllers(app=app, get_uuid=self.uuid, volumemodel=self.volmodel)
        layout_controllers(app=app, get_uuid=self.uuid)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        if self.csvfile_vol is not None:
            store_functions = [(read_csv, [{"csv_file": self.csvfile_vol}])]
            if self.csvfile_parameters is not None:
                store_functions.append(
                    (read_csv, [{"csv_file": self.csvfile_parameters}])
                )
        else:
            function_args: dict = {
                "ensemble_set_model": self.emodel,
                "volfolder": self.volfolder,
                "volfiles": self.volfiles,
            }
            store_functions = [(extract_volumes, [function_args])]
            store_functions.extend(self.emodel.webvizstore)
        return store_functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file)
