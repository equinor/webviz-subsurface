from typing import Callable, List
from enum import unique, Enum
import plotly.graph_objects as go
from dash import html, dcc
import webviz_core_components as wcc
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic
)
from webviz_subsurface_components import DeckGLMap
from ._utils import MapAttribute
# Local import?
from .._map_viewer_fmu.color_tables import default_color_tables


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
    PLUME_POLYGON_LAYER = "plume-polygon-layer"

    CONTOUR_PROPERTY = "contour-property"
    CONTOUR_THRESHOLD = "contour-threshold"
    CONTOUR_SMOOTHING = "contour-smoothing"
    PROPERTY = "property"
    ENSEMBLEINPUT = "ensembleinput"
    REALIZATIONINPUT = "realizationinput"
    DATEINPUT = "dateinput"
    FORMATION_INPUT = "formation-input"
    COLORMAP_INPUT = "colormap-input"

    COLOR_RANGE_MIN_AUTO = "color-range-min-auto"
    COLOR_RANGE_MIN_VALUE = "color-range-min-value"
    COLOR_RANGE_MAX_AUTO = "color-range-max-auto"
    COLOR_RANGE_MAX_VALUE = "color-range-max-value"

    ENSEMBLEBARPLOT = "ensemblebarplot"
    ENSEMBLETIMELEAKPLOT = "ensembletimeleakplot"
    STATISTIC_INPUT = "statistic-input"

    DATE_STORE = "date-store"
    COLOR_RANGE_STORE = "color-range-store"


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
        "flex": 11,
    }
    MAP_WRAPPER = {
        "padding": "2vh",
        "height": "90%",
        "position": "relative",
    }
    PLOT_VIEW = {
        "flex": 9,
        "display": "flex",
        "flex-direction": "row",
        "justify-content": "space-evenly",
    }
    COLORMAP_RANGE = {
        "display": "flex",
        "flex-direction": "row",
    }


def main_layout(get_uuid: Callable, ensembles: List[str]) -> html.Div:
    return html.Div(
        [
            wcc.Frame(
                style=LayoutStyle.SIDEBAR,
                children=[
                    EnsembleSelectorLayout(get_uuid, ensembles),
                    FilterSelectorLayout(get_uuid),
                    MapSelectorLayout(get_uuid),
                    PlumeContourLayout(get_uuid),
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
                                        colorTables=default_color_tables,
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
            ),
            dcc.Store(id=get_uuid(LayoutElements.DATE_STORE)),
            dcc.Store(id=get_uuid(LayoutElements.COLOR_RANGE_STORE)),
        ],
        style=LayoutStyle.PARENTDIV,
    )


class FilterSelectorLayout(wcc.Selectors):
    def __init__(self, get_uuid: Callable):
        super().__init__(
            label="Filter Settings",
            children=[
                "Formation",
                wcc.Dropdown(
                    id=get_uuid(LayoutElements.FORMATION_INPUT),
                ),
                "Date",
                html.Div(
                    [
                        dcc.Slider(
                            id=get_uuid(LayoutElements.DATEINPUT),
                            step=None,
                            marks={0: ''},
                            value=0,
                        ),
                    ],
                    style={
                        "padding-bottom": "50px",
                    }
                ),
            ]
        )


class MapSelectorLayout(wcc.Selectors):
    def __init__(self, get_uuid: Callable):
        super().__init__(
            label="Map Settings",
            open_details=True,
            children=[
                html.Div(
                    [
                        "Property",
                        wcc.Dropdown(
                            id=get_uuid(LayoutElements.PROPERTY),
                            options=[
                                dict(label=m.value, value=m.value)
                                for m in MapAttribute
                            ],
                            value=MapAttribute.MIGRATION_TIME,
                            clearable=False,
                        ),
                        "Statistic",
                        wcc.Dropdown(
                            id=get_uuid(LayoutElements.STATISTIC_INPUT),
                            options=[s.value for s in SurfaceStatistic],
                            value=SurfaceStatistic.MEAN,
                        ),
                        "Color Scale",
                        dcc.Dropdown(
                            id=get_uuid(LayoutElements.COLORMAP_INPUT),
                            options=[d["name"] for d in default_color_tables],
                            value=default_color_tables[0]["name"],
                        ),
                        "Minimum",
                        html.Div(
                            [
                                dcc.Input(id=get_uuid(LayoutElements.COLOR_RANGE_MIN_VALUE), type="number"),
                                dcc.Checklist(["Auto"], ["Auto"], id=get_uuid(LayoutElements.COLOR_RANGE_MIN_AUTO)),
                            ],
                            style=LayoutStyle.COLORMAP_RANGE,
                        ),
                        "Maximum",
                        html.Div(
                            [
                                dcc.Input(id=get_uuid(LayoutElements.COLOR_RANGE_MAX_VALUE), type="number"),
                                dcc.Checklist(["Auto"], ["Auto"], id=get_uuid(LayoutElements.COLOR_RANGE_MAX_AUTO)),
                            ],
                            style=LayoutStyle.COLORMAP_RANGE,
                        ),
                    ],
                    style={
                        "display": "grid",
                        "grid-template-columns": "2fr 3fr",
                        "grid-template-rows": "repeat(5, 1fr)",
                        "align-items": "center",
                    }
                )
            ],
        )


class PlumeContourLayout(wcc.Selectors):
    def __init__(self, get_uuid):
        super().__init__(
            label="Plume Contours",
            children=[
                dcc.Dropdown(
                    id=get_uuid(LayoutElements.CONTOUR_PROPERTY),
                    options=[
                        dict(label="SGAS", value="max_SGAS"),
                        dict(label="AMFG", value="max_AMFG"),
                    ],
                    placeholder="Contour Property",
                    style={
                        "flex": 1
                    }
                ),
                html.Div(
                    children=[
                        html.Div("Threshold"),
                        dcc.Input(
                            id=get_uuid(LayoutElements.CONTOUR_THRESHOLD),
                            type="number",
                            min=0,
                            value=0.000001,
                            placeholder="Threshold",
                            style={
                                "text-align": "right",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flex-direction": "row",
                        "justify-content": "space-between",
                        "padding-top": "5px",
                        "padding-bottom": "5px",
                    }
                ),
                dcc.Checklist(
                    ["Smooth Contours"],
                    ["Smooth Contours"],
                    id=get_uuid(LayoutElements.CONTOUR_SMOOTHING),
                    style={
                        "display": "flex",
                        "align-items": "center",
                    }
                ),
            ],
        )


class EnsembleSelectorLayout(wcc.Selectors):
    def __init__(self, get_uuid: Callable, ensembles: List[str]):
        super().__init__(
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
                    multi=True,
                ),
            ]
        )


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
                    config={
                        "displayModeBar": False,
                    }
                ),
            ],
            **kwargs,
        )
