from pathlib import Path
from typing import Dict, List, Type

import pandas as pd
from dash import Dash
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_subsurface._providers import EnsembleSummaryProvider

from .._simulation_time_series.types.provider_set import (
    create_lazy_provider_set_from_paths,
)
from ._plugin_ids import PluginIds
from .shared_settings import Filter, BarLineSettings
from .views import FanView, BarView, LineView
from ._error import error


class BhpAnalyzer(WebvizPluginABC):
    """QC simulated bottom hole pressures (BHP) from reservoir simulations.

    Can be used to check if your simulated BHPs are in a realistic range.
    E.g. check if your simulated bottom hole pressures are very low in producers,
    or very high injectors.
    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`rel_file_pattern`:** path to `.arrow` files with summary data.
    ---
    Data is read directly from the arrow files with the raw frequency (not resampled).
    Resampling and csvs are not supported to avoid potential of interpolation, which
    might cover extreme BHP values.

    """

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        wells: List[str] = None,
    ):
        super().__init__()

        self.error_message = ""

        self.ens_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        self._input_provider_set = create_lazy_provider_set_from_paths(
            self.ens_paths,
            rel_file_pattern,
        )

        dfs = []
        column_keys = {}
        for ens_name in ensembles:
            ens_provider = self._input_provider_set.provider(ens_name)
            column_keys[ens_name] = _get_wbhp_vectors(ens_provider, wells)
            df = ens_provider.get_vectors_df(column_keys[ens_name], None)
            df["ENSEMBLE"] = ens_name
            dfs.append(df.loc[:, (df != 0).any(axis=0)])  # remove zero-columns

        self.smry = pd.concat(dfs)
        self.theme = webviz_settings.theme

        self.add_store(
            PluginIds.Stores.SELECTED_ENSEMBLE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_SORT_BY, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_ASCENDING_DESCENDING,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PluginIds.Stores.SELECTED_MAX_NUMBER_OF_WELLS,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PluginIds.Stores.SELECTED_WELLS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_STATISTICS, WebvizPluginABC.StorageType.SESSION
        )

        self.add_shared_settings_group(
            Filter(self.smry), PluginIds.SharedSettings.FILTER
        )
        self.add_view(
            FanView(self.smry, webviz_settings),
            PluginIds.BhpID.FAN_CHART,
        )
        self.add_view(
            BarView(self.smry, webviz_settings),
            PluginIds.BhpID.BAR_CHART,
        )
        self.add_view(
            LineView(self.smry, webviz_settings),
            PluginIds.BhpID.LINE_CHART,
        )
        print()
        self.add_shared_settings_group(
            BarLineSettings(),
            PluginIds.SharedSettings.BARLINE_SETTINGS,
            [
                self.view(PluginIds.BhpID.BAR_CHART).get_unique_id().to_string(),
                self.view(PluginIds.BhpID.LINE_CHART).get_unique_id().to_string(),
            ],
        )

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(PluginIds.BhpID.BAR_CHART).get_unique_id().to_string(),
                "content": (
                    "Dashboard for BHP QC:"
                    "Check that simulated bottom hole pressures are realistic."
                ),
            },
            {
                "id": self.view(PluginIds.BhpID.LINE_CHART).get_unique_id().to_string(),
                "content": "Select ensemble to QC.",
            },
            {
                "id": self.view(PluginIds.BhpID.FAN_CHART).get_unique_id().to_string(),
                "content": "Sort wells left to right according to this value.",
            },
            {
                "id": self.shared_settings_group(PluginIds.SharedSettings.FILTER)
                .get_unique_id()
                .to_string(),
                "content": (
                    "Show max selected number of top ranked wells after sorting and filtering."
                ),
            },
            {"id": self.uuid("wells"), "content": "Filter wells."},
        ]

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)


# ---------------------------
def _get_wbhp_vectors(
    ens_provider: EnsembleSummaryProvider,
    wells: List[str] = None,
) -> list:
    """Return list of WBHP vectors. If wells arg is None, return for all wells."""

    if wells is not None:
        return [f"WBHP:{well}" for well in wells]

    wbhp_vectors = [
        vector for vector in ens_provider.vector_names() if vector.startswith("WBHP:")
    ]
    if not wbhp_vectors:
        raise RuntimeError("No WBHP vectors found.")

    return wbhp_vectors
