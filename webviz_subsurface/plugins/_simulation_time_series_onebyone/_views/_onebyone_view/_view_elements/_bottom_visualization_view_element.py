import webviz_core_components as wcc
from dash import dash_table, html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class BottomVisualizationViewElement(ViewElementABC):
    class Ids(StrEnum):
        TABLE_WRAPPER = "table-wrapper"
        TABLE = "table"
        REAL_GRAPH_WRAPPER = "real-graph-wrapper"
        REAL_GRAPH = "real-graph"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    id=self.register_component_unique_id(self.Ids.TABLE_WRAPPER),
                    style={"display": "block"},
                    children=dash_table.DataTable(
                        id=self.register_component_unique_id(self.Ids.TABLE),
                        sort_action="native",
                        sort_mode="multi",
                        filter_action="native",
                        style_as_list_view=True,
                        style_table={"height": "35vh", "overflowY": "auto"},
                    ),
                ),
                html.Div(
                    id=self.register_component_unique_id(self.Ids.REAL_GRAPH_WRAPPER),
                    style={"display": "none"},
                    children=wcc.Graph(
                        config={"displayModeBar": False},
                        style={"height": "35vh"},
                        id=self.register_component_unique_id(self.Ids.REAL_GRAPH),
                    ),
                ),
            ]
        )
