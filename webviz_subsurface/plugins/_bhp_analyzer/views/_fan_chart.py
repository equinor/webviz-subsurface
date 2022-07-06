from typing import List, Union
import math
import re

from dash import callback, Input, Output
from dash.development.base_component import Component
import pandas as pd
import plotly.colors
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC
import webviz_core_components as wcc

from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._view_functions import filter_df, _get_fanchart_traces, calc_statistics
from ...._utils.unique_theming import unique_colors

class FanView(ViewABC):
    class Ids:
        #pylint: disable=too-few-public-methods
        FAN_CHART = "fan-chart"
    def __init__(self, bhp_df: pd.DataFrame, webviz_settings: WebvizSettings,) -> None:
        super().__init__("Fan chart")

        self.bhp_df = bhp_df
        
        column = self.add_column()
        column.add_view_element(Graph(), FanView.Ids.FAN_CHART)
        self.theme = webviz_settings.theme
    
    @property
    def ens_colors(self) -> dict:
        return unique_colors(self.ensembles, self.theme)

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
        def _update_plot(
            ensemble: str,
            n_wells: int,
            wells: Union[str, List[str]],
            sort_by: str,
            ascending: bool,
        ) -> dict:

            wells = wells if isinstance(wells, list) else [wells]
            df = filter_df(df=self.smry, ensemble=ensemble, wells=wells)
            stat_df = (
                calc_statistics(df)
                .sort_values(sort_by, ascending=ascending)
                .iloc[0:n_wells, :]
            )
            fan_traces = _get_fanchart_traces(
                        ens_stat_df=stat_df,
                        color=self.ens_colors[ensemble],
                        legend_group=ensemble,
                    )
            layout = self.theme.create_themed_layout(
                {
                    "yaxis": {
                        "side": "left",
                        "title": "Bottom hole pressure",
                        "showgrid": True,
                    },
                    "yaxis2": {
                        "side": "right",
                        "overlaying": "y",
                        "title": "Count (data points)",
                        "showgrid": False,
                    },
                    "xaxis": {"showgrid": False},
                    "barmode": "group",
                    "legend": {"x": 1.05},
                }
            )
            return {"data": fan_traces, "layout": layout}
