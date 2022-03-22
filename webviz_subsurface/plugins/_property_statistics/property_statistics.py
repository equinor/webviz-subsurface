from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from dash import Dash, dcc
from webviz_config import WebvizConfigTheme, WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin_arguments

from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProviderFactory,
    Frequency,
)

from .controllers.property_delta_controller import property_delta_controller
from .controllers.property_qc_controller import property_qc_controller
from .controllers.property_response_controller import property_response_controller
from .data_loaders import read_csv
from .models import (
    PropertyStatisticsModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)
from .utils.surface import generate_surface_table, get_path
from .views.main_view import main_view


def check_deprecation_argument(
    csvfile_statistics: Optional[Path], csvfile_smry: Optional[Path]
) -> Optional[Tuple[str, str]]:
    if any(elm is not None for elm in [csvfile_statistics, csvfile_smry]):
        return (
            "The usage of aggregated csvfiles as user input options are deprecated. "
            "Please provide feedback if you see a need for a continuation "
            "of this functionality ",
            "",
        )
    return None


class PropertyStatistics(WebvizPluginABC):
    """This plugin visualizes ensemble statistics calculated from grid properties.

---
**The main input to this plugin is property statistics extracted from grid models.
See the documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
Additional data includes UNSMRY data and optionally irap binary surfaces stored in standardized \
FMU format.


**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`statistic_file`:** Csv file for each realization with property statistics. See the \
    documentation in [fmu-tools](http://fmu-docs.equinor.com/) on how to generate this data.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.
* **`surface_renaming`:** Optional dictionary to rename properties/zones to match filenames \
    stored on FMU standardized format (zone--property.gri)

---

?> `Arrow` format for simulation time series data can be generated using the `ECL2CSV` forward \
model in ERT. On existing ensembles the command line tool `smry2arrow_batch` can be used to \
generate arrow files.

?> Folders with statistical surfaces are assumed located at \
`<ensemble_path>/share/results/maps/<ensemble>/<statistic>` where `statistic` are subfolders \
with statistical calculation: `mean`, `stddev`, `p10`, `p90`, `min`, `max`.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency \
(like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.


"""

    # pylint: disable=too-many-arguments, too-many-locals
    @deprecated_plugin_arguments(check_deprecation_argument)
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        statistics_file: str = "share/results/tables/gridpropstatistics.csv",
        surface_renaming: Optional[dict] = None,
        time_index: str = "monthly",
        csvfile_statistics: Optional[Path] = None,
        csvfile_smry: Optional[Path] = None,
    ):
        super().__init__()
        self.theme: WebvizConfigTheme = webviz_settings.theme
        self.statistics_file = statistics_file
        self.ensembles = ensembles
        self.csvfile_statistics = csvfile_statistics
        self.csvfile_smry = csvfile_smry
        self._surface_folders: Union[dict, None]
        self._vmodel: Optional[
            Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel]
        ]

        table_provider = EnsembleTableProviderFactory.instance()

        if ensembles is not None:
            ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            resampling_frequency = Frequency(time_index)
            provider_factory = EnsembleSummaryProviderFactory.instance()

            try:
                self._vmodel = ProviderTimeSeriesDataModel(
                    provider_set={
                        ens: provider_factory.create_from_arrow_unsmry_presampled(
                            str(ens_path), rel_file_pattern, resampling_frequency
                        )
                        for ens, ens_path in ensemble_paths.items()
                    },
                )
            except ValueError as error:
                message = (
                    f"No arrow files found at {rel_file_pattern}. If no arrow files have been "
                    "generated with `ERT` using `ECL2CSV`, the commandline tool "
                    "`smry2arrow_batch` can be used to generate arrow files for an ensemble"
                )
                raise ValueError(message) from error

            propertyproviderset = (
                table_provider.create_provider_set_from_per_realization_csv_file(
                    ensemble_paths, self.statistics_file
                )
            )
            self._surface_folders = {
                ens: Path(ens_path.split("realization")[0]) / "share/results/maps" / ens
                for ens, ens_path in ensemble_paths.items()
            }

        else:
            if self.csvfile_statistics is None:
                raise ValueError(
                    "If not 'ensembles', then csvfile_statistics must be provided"
                )
            propertyproviderset = (
                table_provider.create_provider_set_from_aggregated_csv_file(
                    self.csvfile_statistics
                )
            )
            self._vmodel = (
                SimulationTimeSeriesModel(dataframe=read_csv(csvfile_smry))
                if csvfile_smry is not None
                else None
            )
            self._surface_folders = None

        self._pmodel = PropertyStatisticsModel(
            provider=propertyproviderset, theme=self.theme
        )

        self._surface_renaming = surface_renaming if surface_renaming else {}
        self._surface_table = generate_surface_table(
            statistics_dframe=self._pmodel.dataframe,
            ensembles=self._pmodel.ensembles,
            surface_folders=self._surface_folders,
            surface_renaming=self._surface_renaming,
        )
        self.set_callbacks(app)

    @property
    def layout(self) -> dcc.Tabs:
        return main_view(
            get_uuid=self.uuid,
            property_model=self._pmodel,
            surface_folders=self._surface_folders,
            vector_model=self._vmodel,
        )

    def set_callbacks(self, app: Dash) -> None:
        property_qc_controller(app=app, get_uuid=self.uuid, property_model=self._pmodel)
        if len(self._pmodel.ensembles) > 1:
            property_delta_controller(
                app=app,
                get_uuid=self.uuid,
                property_model=self._pmodel,
                surface_table=self._surface_table,
            )
        if self._vmodel is not None:
            property_response_controller(
                app=app,
                get_uuid=self.uuid,
                surface_table=self._surface_table,
                property_model=self._pmodel,
                timeseries_model=self._vmodel,
            )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store: List[Tuple[Callable, list]] = []
        if self.ensembles is None and self.csvfile_smry is not None:
            store.append((read_csv, [{"csv_file": self.csvfile_smry}]))

        store.append(
            (
                generate_surface_table,
                [
                    {
                        "statistics_dframe": self._pmodel.dataframe,
                        "ensembles": self._pmodel.ensembles,
                        "surface_folders": self._surface_folders,
                        "surface_renaming": self._surface_renaming,
                    }
                ],
            )
        )
        if self._surface_folders is not None:
            for path in self._surface_table["path"].unique():
                store.append((get_path, [{"path": Path(path)}]))
        return store
