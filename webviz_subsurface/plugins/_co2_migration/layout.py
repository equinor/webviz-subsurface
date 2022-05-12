from typing import Callable, List, Any, Dict
from enum import unique, Enum
import plotly.graph_objects as go
from dash import html, dcc
import webviz_core_components as wcc
from webviz_subsurface_components import DeckGLMap
from ._utils import MapAttribute


@unique
class LayoutElements(str, Enum):
    MAP_VIEW = "map-view"
    CONTENT_VIEW = "content-view"
    PLOT_VIEW = "plot-view"
    DECKGLMAP = "deckglmap"
    COLORMAPLAYER = "colormaplayer"
    FAULTPOLYGONSLAYER = "faultpolygonslayer"
    LICENSEBOUNDARYLAYER = "licenseboundarylayer"
    WELLPICKSLAYER = "wellpickslayer"

    PROPERTY = "property"
    ENSEMBLEINPUT = "ensembleinput"
    REALIZATIONINPUT = "realizationinput"
    DATEINPUT = "dateinput"
    FAULTPOLYGONINPUT = "faultpolygoninput"
    WELLPICKZONEINPUT = "wellpickzoneinput"
    MAPZONEINPUT = "mapzoneinput"

    ENSEMBLEBARPLOT = "ensemblebarplot"
    ENSEMBLETIMELEAKPLOT = "ensembletimeleakplot"


@unique
class LayoutLabels(str, Enum):
    LICENSE_BOUNDARY_LAYER = "License Boundary"


class LayoutStyle:
    ENSEMBLE_PLOT_HEIGHT = 300
    ENSEMBLE_PLOT_WIDTH = 400
    PARENTDIV = {
        "display": "flex",
        "height": "84vh",
    }
    SIDEBAR = {
        "flex": 1
    }
    CONTENT_PARENT = {
        "flex": 3,
        "display": "flex",
        "flex-direction": "column",
    }
    MAP_VIEW = {
        "flex": 2,
    }
    MAP_WRAPPER = {
        "padding": "2vh",
        "height": "90%",
        "position": "relative",
    }
    PLOT_VIEW = {
        "flex": 1,
        "display": "flex",
        "flex-direction": "row",
        "justify-content": "center",
    }


def main_layout(get_uuid: Callable, ensembles: List[str]) -> html.Div:
    return html.Div(
        [
            wcc.Frame(
                style=LayoutStyle.SIDEBAR,
                children=[
                    EnsembleSelectorLayout(get_uuid, ensembles),
                    PropertySelectorLayout(get_uuid),
                    DateSelectorLayout(get_uuid),
                    ZoneSelectorLayout(get_uuid),
                ]
            ),
            html.Div(
                [
                    wcc.Frame(
                        id=get_uuid(LayoutElements.MAP_VIEW),
                        color="white",
                        highlight=False,
                        children=[
                            html.Div(
                                [
                                    DeckGLMap(
                                        id=get_uuid(LayoutElements.DECKGLMAP),
                                        layers=[],
                                        coords={"visible": True},
                                        scale={"visible": True},
                                        coordinateUnit="m",
                                        zoom=-7,
                                    ),
                                ],
                                style=LayoutStyle.MAP_WRAPPER,
                            ),
                        ],
                        style=LayoutStyle.MAP_VIEW,
                    ),
                    wcc.Frame(
                        id=get_uuid(LayoutElements.PLOT_VIEW),
                        style=LayoutStyle.PLOT_VIEW,
                        children=SummaryGraphLayout(get_uuid).children
                    )
                ],
                style=LayoutStyle.CONTENT_PARENT
            )
        ],
        style=LayoutStyle.PARENTDIV,
    )


class FullScreen(wcc.WebvizPluginPlaceholder):
    # TODO: this class is a direct copy from MapViewerFMU
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


class PropertySelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable):
        super().__init__(children=wcc.Selectors(
            label="Property",
            open_details=True,
            children=[
                html.Div(
                    [
                        wcc.Dropdown(
                            id=get_uuid(LayoutElements.PROPERTY),
                            options=[
                                dict(label=m.value, value=m.value)
                                for m in MapAttribute
                            ],
                            value=MapAttribute.MIGRATION_TIME,
                            clearable=False,
                        )
                    ] 
                )
            ]
        ))


class EnsembleSelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable, ensembles: List[str]):
        super().__init__(children=wcc.Selectors(
            label="Ensemble",
            open_details=True,
            children=[
                "Ensemble",
                wcc.Dropdown(
                    id=get_uuid(LayoutElements.ENSEMBLEINPUT),
                    options=[
                        dict(value=en, label=en)
                        for en in ensembles
                    ],
                    value=ensembles[0]
                ),
                "Realization",
                wcc.Dropdown(
                    id=get_uuid(LayoutElements.REALIZATIONINPUT),
                ),
            ]
        ))


class SummaryGraphLayout(html.Div):
    def __init__(self, get_uuid: Callable, **kwargs):
        super().__init__(
            children=[
                dcc.Graph(
                    id=get_uuid(LayoutElements.ENSEMBLEBARPLOT),
                    figure=go.Figure(),
                    config={
                        "displayModeBar": False,
                    }
                ),
                dcc.Graph(
                    id=get_uuid(LayoutElements.ENSEMBLETIMELEAKPLOT),
                    figure=go.Figure(),
                    # config={},
                ),
            ],
            **kwargs,
        )


class DateSelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable):
        super().__init__(children=wcc.Selectors(
            label="Dates",
            open_details=True,
            children=[
                dcc.Slider(
                    id=get_uuid(LayoutElements.DATEINPUT),
                    step=None,
                    marks={0: ''},
                    value=0,
                    tooltip={"placement": "bottom", "always_visible": False},
                    # TODO: add arrows for next/previous date?
                )
            ]
        ))


class ZoneSelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable):
        super().__init__(
            children=wcc.Selectors(
                label="Zones and Horizons",
                children=[
                    "Fault Polygons",
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.FAULTPOLYGONINPUT),
                    ),
                    "Well Picks",
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.WELLPICKZONEINPUT)
                    ),
                    "Color Map",
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.MAPZONEINPUT),
                    ),
                ]
            )
        )
