import datetime
from typing import Dict, List, Set, Tuple, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import ALL, Input, Output, State, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import WellOverviewFigure, format_well_overview_figure
from .._plugin_ids import PluginIds
from .._types import ChartType
from .._view_elements import Graph
from ._settings import ControlSettings


class ControlView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        BAR_CHART = "bar-chart"
        PLOT_SETTINGS = "plot-settings"
        FILTER = "filter"
        MAIN_COLUMN = "main-column"
        GRAPH = "graph"

    def __init__(
        self,
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well Control")

        self.data_models = data_models
        self.theme = theme

        self.add_settings_group(
            ControlSettings(self.data_models), ControlView.Ids.PLOT_SETTINGS
        )

        self.main_column = self.add_column(ControlView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback()
        def _update_graph() -> List[Component]:

            return []
