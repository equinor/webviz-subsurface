from typing import List, Type

import webviz_core_components as wcc
from dash import dash_table, dcc, html
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._plugin_ids import PlugInIDs

# omstrukturer og lage et view element for hver ting
# altså ikke trøkke alt in i en Div, men dele den opp
# lage en egen label klasse
# også lage en egen bar og en egen table
# også må man fikse en måte at de ikke vises samtidig, 
# tror det kan bli vanskelig

class TornadoViewElement(ViewElementABC):

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
                        html.Div(
                            id=self.register_component_unique_id(
                                TornadoViewElement.IDs.BAR_WRAPPER
                            ),
                            style={"display": "inline"},
                            # The graph element that shows the data (bars)
                            children=wcc.Graph(
                                id=self.register_component_unique_id(TornadoViewElement.IDs.TORNADO_BAR),
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
                # vet ikke om jeg trenger disse egt
                dcc.Store(id = self.get_store_unique_id(PlugInIDs.Stores.DataStores.TORNADO_DATA),storage_type=WebvizPluginABC.StorageType.SESSION),
                dcc.Store(id = self.get_store_unique_id(PlugInIDs.Stores.DataStores.CLICK_DATA),storage_type=WebvizPluginABC.StorageType.SESSION),
                dcc.Store(id = self.get_store_unique_id(PlugInIDs.Stores.DataStores.HIGH_LOW),storage_type=WebvizPluginABC.StorageType.SESSION),
                dcc.Store(id = self.get_store_unique_id(PlugInIDs.Stores.DataStores.CLIENT_HIGH_PIXELS),storage_type=WebvizPluginABC.StorageType.SESSION),
            ],
        )
