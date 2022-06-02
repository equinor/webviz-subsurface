from typing import List, Tuple

from dash.development.base_component import Component
from dash import callback, Input, Output, html
from webviz_config.webviz_plugin_subclasses import ViewElementABC
import webviz_subsurface_components as wsc

from ..._layout_elements import ElementIds


class DeckGLView(ViewElementABC):
    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> Component:

        return html.Div(
            style={"height": "90vh"},
            children=wsc.DeckGLMap(
                id=self.register_component_unique_id(ElementIds.DECKGLVIEW.VIEW),
                layers=[
                    {
                        "@@type": "ColormapLayer",
                    },
                ],
                bounds=[0, 0, 100, 100],
                views={
                    "layout": [1, 1],
                    "showLabel": True,
                    "viewports": [
                        {
                            "id": "one",
                            "layerIds": ["colormap-layer"],
                            "show3D": False,
                            "name": "test",
                        }
                    ],
                },
            ),
        )
