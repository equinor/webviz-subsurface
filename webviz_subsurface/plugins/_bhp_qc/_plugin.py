from pathlib import Path
from typing import Dict, List

import pandas as pd
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._utils.ensemble_summary_provider_set_factory import (
    create_lazy_ensemble_summary_provider_set_from_paths,
)

from ._plugin_ids import PluginIds
from .shared_settings import Filter, ViewSettings
from .view_elements import Graph
from .views import BarView, FanView, LineView


class BhpQc(WebvizPluginABC):
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
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        wells: List[str] = None,
    ):
        super().__init__()

        if ensembles is None:
            raise ValueError("Enembles needs to be provided")

        self.ens_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        self._input_provider_set = create_lazy_ensemble_summary_provider_set_from_paths(
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

        self.add_view(
            LineView(self.smry, webviz_settings),
            PluginIds.BhpId.LINE_CHART,
        )
        self.add_view(
            FanView(self.smry, webviz_settings),
            PluginIds.BhpId.FAN_CHART,
        )
        self.add_view(
            BarView(self.smry, webviz_settings),
            PluginIds.BhpId.BAR_CHART,
        )

        self.add_shared_settings_group(
            Filter(self.smry), PluginIds.SharedSettings.FILTER
        )
        self.add_shared_settings_group(
            ViewSettings(),
            PluginIds.SharedSettings.VIEW_SETTINGS,
            [
                self.view(PluginIds.BhpId.BAR_CHART).get_unique_id().to_string(),
                self.view(PluginIds.BhpId.LINE_CHART).get_unique_id().to_string(),
            ],
        )

        # set start-up view (only affects first time use)
        self.set_active_view_id(PluginIds.BhpId.LINE_CHART)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(PluginIds.BhpId.FAN_CHART)
                .view_element(FanView.Ids.FAN_CHART)
                .component_unique_id(Graph.Ids.GRAPH),
                "content": (
                    "Dashboard for BHP QC: "
                    "Check that simulated bottom hole pressures are realistic."
                    " Can be viewed in a Fan chart,"
                ),
            },
            {
                "id": self.view(PluginIds.BhpId.LINE_CHART)
                .view_element(LineView.Ids.LINE_CHART)
                .component_unique_id(Graph.Ids.GRAPH),
                "content": ("Line chart"),
            },
            {
                "id": self.view(PluginIds.BhpId.BAR_CHART)
                .view_element(BarView.Ids.BAR_CHART)
                .component_unique_id(Graph.Ids.GRAPH),
                "content": ("and Bar chart."),
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.FILTER
                ).component_unique_id(Filter.Ids.ENSEMBLE),
                "content": "Select ensemble to QC.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.FILTER
                ).component_unique_id(Filter.Ids.SORT_BY),
                "content": "Sort wells left to right according to this value.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.FILTER
                ).component_unique_id(Filter.Ids.MAX_NUMBER_OF_WELLS_SLIDER),
                "content": (
                    "Show max selected number of top ranked wells after sorting and filtering."
                ),
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.FILTER
                ).component_unique_id(Filter.Ids.WELLS),
                "content": "Filter wells.",
            },
        ]


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
