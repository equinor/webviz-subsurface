from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from dash import Dash, dcc
from webviz_config import WebvizConfigTheme, WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin_arguments
from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO, WebvizRunMode

from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)
from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProvider,
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
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
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
        column_keys: Optional[list] = None,
        csvfile_statistics: Path = None,
        csvfile_smry: Path = None,
    ):
        super().__init__()
        self.theme: WebvizConfigTheme = webviz_settings.theme
        self.ensembles = ensembles
        self._surface_folders: Union[dict, None] = None
        self._vmodel: Optional[
            Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel]
        ] = None
        run_mode_portable = WEBVIZ_INSTANCE_INFO.run_mode == WebvizRunMode.PORTABLE
        table_provider_factory = EnsembleTableProviderFactory.instance()

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
                provider_set = {
                    ens: provider_factory.create_from_arrow_unsmry_presampled(
                        str(ens_path), rel_file_pattern, resampling_frequency
                    )
                    for ens, ens_path in ensemble_paths.items()
                }
                self._vmodel = ProviderTimeSeriesDataModel(
                    provider_set=provider_set, column_keys=column_keys
                )
                table_provider_set = {
                    ens: table_provider_factory.create_from_per_realization_csv_file(
                        ens_path, statistics_file
                    )
                    for ens, ens_path in ensemble_paths.items()
                }
                property_df = create_df_from_table_provider(table_provider_set)

            except ValueError as error:
                message = (
                    f"Some/all ensembles are missing arrow files at {rel_file_pattern}.\n"
                    "If no arrow files have been generated with `ERT` using `ECL2CSV`, "
                    "the commandline tool `smry2arrow_batch` can be used to generate arrow "
                    "files for an ensemble"
                )
                if not run_mode_portable:
                    raise ValueError(message) from error

                # NOTE: this part below is to ensure backwards compatibility for portable app's
                # created before the arrow support. It should be removed in the future.
                emodel: EnsembleSetModel = (
                    caching_ensemble_set_model_factory.get_or_create_model(
                        ensemble_paths=ensemble_paths,
                        time_index=time_index,
                        column_keys=column_keys,
                    )
                )
                self._vmodel = SimulationTimeSeriesModel(
                    dataframe=emodel.get_or_load_smry_cached()
                )
                property_df = emodel.load_csv(csv_file=Path(statistics_file))

            self._surface_folders = {
                ens: Path(ens_path.split("realization")[0]) / "share/results/maps" / ens
                for ens, ens_path in ensemble_paths.items()
            }

        else:
            if csvfile_statistics is None:
                raise ValueError(
                    "If not 'ensembles', then csvfile_statistics must be provided"
                )
            # NOTE: the try/except is for backwards compatibility with existing portable app's.
            # It should be removed in the future together with the support of aggregated csv-files
            try:
                property_df = create_df_from_table_provider(
                    table_provider_factory.create_provider_set_from_aggregated_csv_file(
                        csvfile_statistics
                    )
                )
            except FileNotFoundError:
                if not run_mode_portable:
                    raise
                property_df = read_csv(csvfile_statistics)

            if csvfile_smry is not None:
                try:
                    smry_df = create_df_from_table_provider(
                        table_provider_factory.create_provider_set_from_aggregated_csv_file(
                            csvfile_smry
                        )
                    )
                except FileNotFoundError:
                    if not run_mode_portable:
                        raise
                    smry_df = read_csv(csvfile_smry)

                self._vmodel = SimulationTimeSeriesModel(dataframe=smry_df)

        self._pmodel = PropertyStatisticsModel(dataframe=property_df, theme=self.theme)

        self._surface_renaming = surface_renaming if surface_renaming else {}
        self._surface_table = generate_surface_table(
            zones=self._pmodel.zones,
            properties=self._pmodel.properties,
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
        store: List[Tuple[Callable, list]] = [
            (
                generate_surface_table,
                [
                    {
                        "zones": self._pmodel.zones,
                        "properties": self._pmodel.properties,
                        "ensembles": self._pmodel.ensembles,
                        "surface_folders": self._surface_folders,
                        "surface_renaming": self._surface_renaming,
                    }
                ],
            )
        ]
        if self._surface_folders is not None:
            for path in self._surface_table["path"].unique():
                store.append((get_path, [{"path": Path(path)}]))
        return store


def create_df_from_table_provider(
    provider_set: Dict[str, EnsembleTableProvider]
) -> pd.DataFrame:
    """Aggregates parameters from all ensemble into a common dataframe."""
    dfs = []
    for ens_name, provider in provider_set.items():
        df = provider.get_column_data(column_names=provider.column_names())
        df["ENSEMBLE"] = ens_name
        dfs.append(df)
    return pd.concat(dfs)
