from typing import List

import webviz_core_components as wcc
from click import style
from dash import dash_table, dcc, html
from dash.development.base_component import Component
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._plugin_ids import PlugInIDs


class TornadoViewElement(ViewElementABC):
    """View element for table view and bar view"""

    class IDs:
        # pylint: disable=too-few-public-methods
        BARS = "bars"
        TABLE = "table"
        TABLE_WRAPPER = "table-wrapper"

    def __init__(self, height="75vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> html.Div:
        return html.Div(
            style={"overflowY": "auto", "height": "60vh"},
            children=[
                wcc.Graph(
                    id=self.register_component_unique_id(TornadoViewElement.IDs.BARS),
                    config={"displayModeBar": True},
                    style={"display": "inline"},
                ),
                html.Div(
                    id=self.register_component_unique_id(
                        TornadoViewElement.IDs.TABLE_WRAPPER
                    ),
                    style={"display": "none"},
                    children=dash_table.DataTable(
                        id=self.register_component_unique_id(
                            TornadoViewElement.IDs.TABLE
                        ),
                        style_cell={"whiteSpace": "normal", "height": "auto"},
                    ),
                ),
            ],
        )
