from typing import List, Union

import pandas as pd
from dash import Input, Output, callback
from webviz_config import WebvizSettings
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._view_functions import calc_statistics, filter_df, label_map


class BarView(ViewABC):
    class Ids(StrEnum):
        BAR_CHART = "bar-chart"
        SETTINGS = "settings"

    def __init__(
        self,
        bhp_df: pd.DataFrame,
        webviz_settings: WebvizSettings,
    ) -> None:
        super().__init__("Bar chart")

        self.bhp_df = bhp_df

        column = self.add_column()
        column.add_view_element(Graph(), BarView.Ids.BAR_CHART)
        self.theme = webviz_settings.theme

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(BarView.Ids.BAR_CHART)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_SORT_BY), "data"),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.SELECTED_ASCENDING_DESCENDING
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_MAX_NUMBER_OF_WELLS),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_STATISTICS), "data"
            ),
        )
        def _update_plot(
            ensemble: str,
            sort_by: str,
            ascending: bool,
            n_wells: int,
            wells: Union[str, List[str]],
            stat_bars: Union[str, List[str]],
        ) -> dict:

            wells = wells if isinstance(wells, list) else [wells]
            stat_bars = stat_bars if isinstance(stat_bars, list) else [stat_bars]
            df = filter_df(df=self.bhp_df, ensemble=ensemble, wells=wells)
            stat_df = (
                calc_statistics(df)
                .sort_values(sort_by, ascending=ascending)
                .iloc[0:n_wells, :]
            )
            bar_chart = []
            for stat in stat_bars:
                yaxis = "y2" if stat == "count" else "y"
                bar_chart.append(
                    {
                        "x": [vec[5:] for vec in stat_df.index],  # strip WBHP:
                        "y": stat_df[stat],
                        "name": [
                            key for key, value in label_map().items() if value == stat
                        ][0],
                        "yaxis": yaxis,
                        "type": "bar",
                        "offsetgroup": stat,
                        "showlegend": True,
                    }
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
            return {"data": bar_chart, "layout": layout}
