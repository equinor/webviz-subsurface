import json
from typing import Callable, List, Any
from dash import html, dcc
import webviz_core_components as wcc
from webviz_subsurface_components import DeckGLMap
from enum import unique, Enum
from ._utils import MapAttribute


@unique
class LayoutElements(str, Enum):
    MAINVIEW = "mainview"
    DECKGLMAP = "deckglmap"
    COLORMAPLAYER = "colormaplayer"
    FAULTPOLYGONSLAYER = "faultpolygonslayer"
    LICENSEBOUNDARYLAYER = "licenseboundarylayer"
    WELLPICKSLAYER = "wellpickslayer"

    PROPERTY = "property"
    ENSEMBLEINPUT = "ensembleinput"
    DATEINPUT = "dateinput"
    FAULTPOLYGONINPUT = "faultpolygoninput"
    WELLPICKZONEINPUT = "wellpickzoneinput"
    MAPZONEINPUT = "mapzoneinput"


class LayoutStyle:
    MAPHEIGHT = "87vh"
    PARENTDIV = {"display": "flex"}
    SIDEBAR = {"flex": 1, "height": "90vh"}
    MAINVIEW = {"flex": 3, "height": "90vh"}
    RESET_BUTTON = {
        "marginTop": "5px",
        "width": "100%",
        "height": "20px",
        "line-height": "20px",
        "background-color": "#7393B3",
        "color": "#fff",
    }


def main_layout(get_uuid: Callable, ensembles: List[str]) -> html.Div:
    return html.Div(
        [
            wcc.Frame(
                style=LayoutStyle.SIDEBAR,
                children=[
                    PropertySelectorLayout(get_uuid),
                    EnsembleSelectorLayout(get_uuid, ensembles),
                    DateSelectorLayout(get_uuid),
                    ZoneSelectorLayout(get_uuid),
                ]
            ),
            wcc.Frame(
                id=get_uuid(LayoutElements.MAINVIEW),
                style=LayoutStyle.MAINVIEW,
                color="white",
                highlight=False,
                children=[
                    FullScreen(
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
                            style={"height": LayoutStyle.MAPHEIGHT},
                        )
                    )
                ]
            ),
        ],
        style=LayoutStyle.PARENTDIV,
    )


class FullScreen(wcc.WebvizPluginPlaceholder):
    # TODO: this class is a direct copy from MapViewerFMU
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


class PropertySelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable):
        super().__init__(children=[
            html.Div(
                [
                    wcc.Dropdown(
                        label="Property",
                        id=get_uuid(LayoutElements.PROPERTY),
                        options=[
                            dict(label=m.value, value=m.value)
                            for m in MapAttribute
                        ],
                        value=MapAttribute.MigrationTime,
                        clearable=False,
                    )
                ] 
            )
        ])


class EnsembleSelectorLayout(html.Div):
    def __init__(self, get_uuid: Callable, ensembles: List[str]):
        super().__init__(children=wcc.Selectors(
            label="Ensemble",
            open_details=True,
            children=[
                wcc.Dropdown(
                    id=get_uuid(LayoutElements.ENSEMBLEINPUT),
                    options=[
                        dict(value=en, label=en)
                        for en in ensembles
                    ],
                    value=ensembles[0]
                )
            ]
        ))


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
                    "Map",
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.MAPZONEINPUT),
                    ),
                ]
            )
        )
