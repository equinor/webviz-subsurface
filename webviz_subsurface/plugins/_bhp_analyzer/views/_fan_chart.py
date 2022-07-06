from typing import List, Union
import math
import re

from dash import callback, Input, Output
from dash.development.base_component import Component
import pandas as pd
import plotly.colors
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC
import webviz_core_components as wcc

from .._plugin_ids import PluginIds
from ..view_elements import Graph

class FanView(ViewABC):
    class Ids:
        #pylint: disable=too-few-public-methods
        FAN_CHART = "fan-chart"
    def __init__(self, bhp_df: pd.DataFrame) -> None:
        super().__init__("Fan chart")

        self.bhp_df = bhp_df
        
        column = self.add_column()
        column.add_view_element(Graph(), FanView.Ids.FAN_CHART)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(FanView.Ids.FAN_CHART)
                .component_unique_id(Graph.Ids.GRAPH).to_string(), "figure",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_SORT_BY), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ASCENDING_DESCENDING), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_MAX_NUMBER_OF_WELLS), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
        )
        def _update_plot(ensemble: str,
            n_wells: int,
            wells: Union[str, List[str]],
            sort_by: str,
            stat_fans: Union[str, List[str]],
            ascending: bool,
        ) -> dict:

            wells = wells if isinstance(wells, list) else [wells]
            
            fan_chart = {}
            return fan_chart
