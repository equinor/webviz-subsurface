from typing import Optional, Union, List, Tuple, Callable
import pathlib

import dash
import dash_core_components as dcc
from webviz_config import WebvizPluginABC
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
from webviz_subsurface._models import EnsembleSetModel
from .views.main_view import main_view
from .models import PropertyStatisticsModel, SimulationTimeSeriesModel
from .controllers.property_qc_controller import property_qc_controller
from .controllers.property_delta_controller import property_delta_controller
from .controllers.property_response_controller import property_response_controller
from .utils.surface import surface_store
from .data_loaders import read_csv


class PropertyStatistics(WebvizPluginABC):
    """This plugin visualizes ensemble statistics calculated from grid properties.

---
**The main input to this plugin is property statistics extracted from grid models.
See the documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
Additional data includes UNSMRY data and optionally irap binary surfaces stored in standardized \
FMU format.

**Input data can be provided in two ways: Aggregated or read from ensembles stored on scratch.**

**Using aggregated data**
* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and \
    vector columns (absolute path or relative to config file).
* **`csvfile_statistics`:** Aggregated `csv` file for property statistics. See the \
    documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.

**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`statistic_file`:** Csv file for each realization with property statistics.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.
* **`surface_renaming`:** Optional dictionary to rename properties/zones to match filenames \
    stored on FMU standardized format (zone--property.gri)

---

?> Folders with statistical surfaces are assumed located at \
`<ensemble_path>/share/results/maps/<ensemble>/<statistic>` where `statistic` are subfolders \
with statistical calculation: `mean`, `stddev`, `p10`, `p90`, `min`, `max`.

!> Surface data is currently not available when using aggregated files.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency \
(like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.


**Using aggregated data**


**Using simulation time series data directly from `.UNSMRY` files**

Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other \
speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: dash.Dash,
        ensembles: Optional[list] = None,
        statistics_file: str = "share/results/tables/gridpropstatistics.csv",
        csvfile_statistics: pathlib.Path = None,
        csvfile_smry: pathlib.Path = None,
        surface_renaming: Optional[dict] = None,
        time_index: str = "monthly",
        column_keys: Optional[list] = None,
    ):
        super().__init__()
        WEBVIZ_ASSETS.add(
            pathlib.Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "container.css"
        )
        # TODO(Sigurd) fix this once we get a separate webviz_settings parameter
        self.theme: WebvizConfigTheme = app.webviz_settings["theme"]
        self.time_index = time_index
        self.column_keys = column_keys
        self.statistics_file = statistics_file
        self.ensembles = ensembles
        self.csvfile_statistics = csvfile_statistics
        self.csvfile_smry = csvfile_smry
        self.surface_folders: Union[dict, None]

        if ensembles is not None:
            self.emodel = EnsembleSetModel(
                ensemble_paths={
                    ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                        ens
                    ]
                    for ens in ensembles
                }
            )
            self.pmodel = PropertyStatisticsModel(
                dataframe=self.emodel.load_csv(
                    csv_file=pathlib.Path(self.statistics_file)
                ),
                theme=self.theme,
            )
            self.vmodel = SimulationTimeSeriesModel(
                dataframe=self.emodel.load_smry(
                    time_index=self.time_index, column_keys=self.column_keys
                ),
                theme=self.theme,
            )
            self.surface_folders = {
                ens: folder / "share" / "results" / "maps" / ens
                for ens, folder in self.emodel.ens_folders.items()
            }
        else:
            self.pmodel = PropertyStatisticsModel(
                dataframe=read_csv(csvfile_statistics), theme=self.theme
            )
            self.vmodel = SimulationTimeSeriesModel(
                dataframe=read_csv(csvfile_smry), theme=self.theme
            )
            self.surface_folders = None

        self.surface_renaming = surface_renaming if surface_renaming else {}

        self.set_callbacks(app)

    @property
    def layout(self) -> dcc.Tabs:
        return main_view(parent=self)

    def set_callbacks(self, app: dash.Dash) -> None:
        property_qc_controller(self, app)
        if len(self.pmodel.ensembles) > 1:
            property_delta_controller(self, app)
        property_response_controller(self, app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store: List[Tuple[Callable, list]] = []
        if self.ensembles is not None:
            store.extend(self.emodel.webvizstore)
        else:
            store.extend(
                [
                    (
                        read_csv,
                        [
                            {"csv_file": self.csvfile_smry},
                            {"csv_file": self.csvfile_statistics},
                        ],
                    )
                ]
            )
        if self.surface_folders is not None:
            store.extend(surface_store(parent=self))
        return store
