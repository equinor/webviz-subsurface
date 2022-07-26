import webviz_core_components as wcc
from dash import dash_table, html
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class TornadoViewElement(ViewElementABC):
    """comment"""

    class IDs:
        # pylint: disable=too-few-public-methods
        TORNADO_VIEW = "tornado-view"
        TORNADO_BAR = "tronado-bar"
        BAR_WRAPPER = "bar-wrapper"
        TORNADO_TABLE = "tornado-table"
        TABLE_WRAPPER = "table_wrapper"
        LABEL = "label"

    def __init__(
        self,
    ) -> None:
        super().__init__()

    # skal vi ha med div?
    def inner_layout(self) -> html.Div:
        return html.Div(
            style={"marginLeft": "10px", "height": "90vh"},
            children=[
                # label
                html.Div(
                    children=[
                        html.Label(
                            "Tornado Plot",
                            style={
                                "textAlign": "center",
                                "font-weight": "bold",
                            },
                        ),
                    ],
                ),
                # rest
                html.Div(
                    style={"overflowY": "auto", "height": "85vh"},
                    children=[
                        # graph
                        html.Div(
                            id=self.register_component_unique_id(
                                TornadoViewElement.IDs.BAR_WRAPPER
                            ),
                            style={"display": "inline"},
                            # The graph element that shows the data (bars)
                            children=wcc.Graph(
                                id=self.register_component_unique_id(
                                    TornadoViewElement.IDs.TORNADO_BAR
                                ),
                                config={"displayModeBar": False},
                            ),
                        ),
                        html.Div(
                            id=self.register_component_unique_id(
                                TornadoViewElement.IDs.TABLE_WRAPPER
                            ),
                            style={"display": "none"},
                            # The element that shows the data (table)
                            children=dash_table.DataTable(
                                id=self.register_component_unique_id(
                                    TornadoViewElement.IDs.TORNADO_TABLE
                                ),
                                style_cell={
                                    "whiteSpace": "normal",
                                    "height": "60vh",
                                },
                            ),
                        ),
                    ],
                ),
            ],
        )
