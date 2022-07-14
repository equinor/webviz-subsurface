import datetime
from typing import Callable, Dict, List, Set

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._types import ChartType


class OverviewSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        #plot controls
        PLOT_TYPE = "plot-type"
        SELECTED_ENSEMBLES = "selected_ensembles"
        SELECTED_RESPONSE = "selected-response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"

        #filters
        SLECTED_WELLS = "selected-wells"
        SELECTED_WELLTYPE = "selected-welltype"

        #plot type
        SHOW_LEGEND = "show-legend"
        OVERLAY_BARS = "overlay-bars"
        SHOW_PROD_AS_TEXT = "show-prod-as-text"
        WHITE_BACKGROUND = "white-background"

        

    def __init__(self,
        data_models: Dict[str, EnsembleWellAnalysisData]
    ) -> None:

        super().__init__("Overview Settings")

        self.ensembles = list(data_models.keys())
        self.dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            self.dates = self.dates.union(ens_data_model.dates)
        self.sorted_dates: List[datetime.datetime] = sorted(list(self.dates))


    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(OverviewSettings.Ids.SELECTED_ENSEMBLES),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(OverviewSettings.Ids.SELECTED_RESPONSE),
                options=[
                    {"label": "Oil production", "value": "WOPT"},
                    {"label": "Gas production", "value": "WGPT"},
                    {"label": "Water production", "value": "WWPT"},
                ],
                value="WOPT",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Only Production after date",
                id=self.register_component_unique_id(OverviewSettings.Ids.ONLY_PRODUCTION_AFTER_DATE),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self.sorted_dates
                ],
                multi=False,
            ),
        ]