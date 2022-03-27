from typing import Callable, Dict, List, Optional
import json

import webviz_core_components as wcc
from dash import html

from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    Hillshading2DLayer,
    DrawingLayer,
    GeoJsonLayer,
)
from webviz_subsurface_components import DeckGLMap


def intersection_and_map_layout(get_uuid: Callable) -> html.Div:
    """Layout for the intersection graph and maps"""
    return html.Div(
        children=[
            wcc.Frame(
                highlight=False,
                color="white",
                children=[
                    wcc.Graph(
                        style={"height": "48vh", "background-color": "white"},
                        id=get_uuid("intersection-graph"),
                    ),
                ],
            ),
            wcc.Frame(
                id=get_uuid("maps-and-uncertainty-table-wrapper"),
                highlight=False,
                color="white",
                children=[
                    wcc.FlexBox(
                        style={"height": "40vh", "display": "flex"},
                        id=get_uuid("all-maps-wrapper"),
                        children=DeckGLMap(
                            id=get_uuid("deckgl"),
                            # editedData={"drawing": {}},
                            layers=[
                                json.loads(layer.to_json())
                                for layer in [
                                    ColormapLayer(uuid="colormap"),
                                    DrawingLayer(),
                                    Hillshading2DLayer(uuid="hillshading"),
                                    ColormapLayer(uuid="colormap2"),
                                    Hillshading2DLayer(uuid="hillshading2"),
                                    ColormapLayer(uuid="colormap3"),
                                    GeoJsonLayer(name="X-line", uuid="x_line"),
                                    GeoJsonLayer(name="Y-line", uuid="y_line"),
                                ]
                            ],
                            zoom=-5,
                        ),
                    ),
                ],
            ),
        ],
    )
