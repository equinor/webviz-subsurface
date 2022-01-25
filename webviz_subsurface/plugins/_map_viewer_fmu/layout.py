from enum import Enum, auto, unique
from typing import Callable, List, Dict, Any, Optional

import webviz_core_components as wcc
from dash import dcc, html


from webviz_subsurface._components.deckgl_map import DeckGLMap  # type: ignore
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    DrawingLayer,
    Hillshading2DLayer,
    WellsLayer,
)
from .providers.ensemble_surface_provider import SurfaceMode
from webviz_subsurface._models import WellSetModel

from .utils.formatting import format_date


@unique
class LayoutElements(str, Enum):
    """Contains all ids used in plugin. Note that some id's are
    used as combinations of LEFT/RIGHT_VIEW together with other elements to
    support pattern matching callbacks."""

    MULTI = auto()
    VIEW_DATA = auto()
    MAINVIEW = auto()
    SELECTED_DATA = auto()
    SELECTIONS = auto()
    COLORSELECTIONS = auto()
    LINK = auto()
    COLORLINK = auto()
    WELLS = auto()
    LOG = auto()
    VIEWS = auto()
    VIEW_COLUMNS = auto()
    DECKGLMAP = auto()
    RANGE_RESET = auto()
    STORED_COLOR_SETTINGS = auto()
    FAULTPOLYGONS = auto()
    WRAPPER = auto()
    COLORWRAPPER = auto()
    RESET_BUTTOM_CLICK = auto()
    SELECTORVALUES = auto()
    COLORMAP_LAYER = "colormaplayer"
    HILLSHADING_LAYER = "hillshadinglayer"
    WELLS_LAYER = "wellayer"


class LayoutLabels(str, Enum):
    """Text labels used in layout components"""

    ATTRIBUTE = "Surface attribute"
    NAME = "Surface name / zone"
    DATE = "Surface time interval"
    ENSEMBLE = "Ensemble"
    MODE = "Aggregation/Simulation/Observation"
    REALIZATIONS = "Realization(s)"
    WELLS = "Wells"
    LOG = "Log"
    COLORMAP_WRAPPER = "Surface coloring"
    COLORMAP_SELECT = "Colormap"
    COLORMAP_RANGE = "Value range"
    RANGE_RESET = "Reset"
    COLORMAP_KEEP_RANGE = "Lock range"
    LINK = "🔗 Link"
    FAULTPOLYGONS = "Fault polygons"
    FAULTPOLYGONS_OPTIONS = "Show fault polygons"


class LayoutStyle:
    """CSS styling"""

    MAPHEIGHT = "87vh"
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


class Tabs(str, Enum):
    CUSTOM = "custom"
    STATS = "stats"
    DIFF = "diff"
    SPLIT = "split"


class TabsLabels(str, Enum):
    CUSTOM = "Custom view"
    STATS = "Map statistics"
    DIFF = "Difference between two maps"
    SPLIT = "Maps per selector"


class DefaultSettings:

    NUMBER_OF_VIEWS = {Tabs.STATS: 4, Tabs.DIFF: 2, Tabs.SPLIT: 1}
    VIEWS_IN_ROW = {Tabs.DIFF: 3}
    LINKED_SELECTORS = {
        Tabs.STATS: ["ensemble", "attribute", "name", "date", "colormap"],
        Tabs.SPLIT: [
            "ensemble",
            "attribute",
            "name",
            "date",
            "mode",
            "realizations",
            "colormap",
        ],
    }
    SELECTOR_DEFAULTS = {
        Tabs.STATS: {
            "mode": [
                SurfaceMode.MEAN,
                SurfaceMode.REALIZATION,
                SurfaceMode.STDDEV,
                SurfaceMode.OBSERVED,
            ]
        },
    }
    COLORMAP_OPTIONS = [
        "Physics",
        "Rainbow",
        "Porosity",
        "Permeability",
        "Seismic BlueWhiteRed",
        "Time/Depth",
        "Stratigraphy",
        "Facies",
        "Gas-Oil-Water",
        "Gas-Water",
        "Oil-Water",
        "Accent",
    ]


class FullScreen(wcc.WebvizPluginPlaceholder):
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


def main_layout(
    get_uuid: Callable,
    well_set_model: Optional[WellSetModel],
    show_fault_polygons: bool = True,
) -> None:

    return wcc.Tabs(
        id=get_uuid("tabs"),
        style={"width": "100%"},
        value=Tabs.CUSTOM,
        children=[
            wcc.Tab(
                label=TabsLabels.CUSTOM,
                value=Tabs.CUSTOM,
                children=view_layout(
                    Tabs.CUSTOM, get_uuid, well_set_model, show_fault_polygons
                ),
            ),
            wcc.Tab(
                label=TabsLabels.DIFF,
                value=Tabs.DIFF,
                children=view_layout(
                    Tabs.DIFF, get_uuid, well_set_model, show_fault_polygons
                ),
            ),
            wcc.Tab(
                label=TabsLabels.STATS,
                value=Tabs.STATS,
                children=view_layout(
                    Tabs.STATS, get_uuid, well_set_model, show_fault_polygons
                ),
            ),
            wcc.Tab(
                label=TabsLabels.SPLIT,
                value=Tabs.SPLIT,
                children=view_layout(
                    Tabs.SPLIT, get_uuid, well_set_model, show_fault_polygons
                ),
            ),
        ],
    )


def view_layout(tab, get_uuid, well_set_model, show_fault_polygons):
    selector_labels = {
        "ensemble": LayoutLabels.ENSEMBLE,
        "attribute": LayoutLabels.ATTRIBUTE,
        "name": LayoutLabels.NAME,
        "date": LayoutLabels.DATE,
        "mode": LayoutLabels.MODE,
    }
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style=LayoutStyle.SIDEBAR,
                children=list(
                    filter(
                        None,
                        [
                            DataStores(tab, get_uuid=get_uuid),
                            ViewSelector(tab, get_uuid=get_uuid),
                            *[
                                MapSelector(tab, get_uuid, selector, label=label)
                                for selector, label in selector_labels.items()
                            ],
                            RealizationSelector(tab, get_uuid=get_uuid),
                            WellsSelector(
                                tab,
                                get_uuid=get_uuid,
                                well_set_model=well_set_model,
                            ),
                            show_fault_polygons
                            and FaultPolygonsSelector(tab, get_uuid=get_uuid),
                            SurfaceColorSelector(tab, get_uuid=get_uuid),
                        ],
                    )
                ),
            ),
            wcc.Frame(
                id=get_uuid(LayoutElements.MAINVIEW),
                style=LayoutStyle.MAINVIEW,
                color="white",
                highlight=False,
                children=FullScreen(
                    html.Div(
                        [
                            DeckGLMap(
                                id={
                                    "id": get_uuid(LayoutElements.DECKGLMAP),
                                    "tab": tab,
                                },
                                layers=update_map_layers(1, well_set_model),
                                bounds=[456063.6875, 5926551, 467483.6875, 5939431],
                            )
                        ],
                        style={"height": LayoutStyle.MAPHEIGHT},
                    ),
                ),
            ),
        ]
    )


class DataStores(html.Div):
    def __init__(self, tab, get_uuid: Callable) -> None:
        super().__init__(
            children=[
                dcc.Store(
                    id={"id": get_uuid(LayoutElements.SELECTED_DATA), "tab": tab}
                ),
                dcc.Store(
                    id={"id": get_uuid(LayoutElements.SELECTORVALUES), "tab": tab}
                ),
                dcc.Store(
                    id={"id": get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "tab": tab}
                ),
                dcc.Store(id=get_uuid(LayoutElements.STORED_COLOR_SETTINGS)),
                dcc.Store(id={"id": get_uuid(LayoutElements.VIEW_DATA), "tab": tab}),
            ]
        )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, tab, get_uuid, selector: str):
        clicked = selector in DefaultSettings.LINKED_SELECTORS.get(tab, [])
        super().__init__(
            id={
                "id": get_uuid(LayoutElements.LINK)
                if selector not in ["color_range", "colormap"]
                else get_uuid(LayoutElements.COLORLINK),
                "tab": tab,
                "selector": selector,
            },
            options=[{"label": LayoutLabels.LINK, "value": selector}],
            value=[selector] if clicked else [],
            style={"display": "none" if clicked else "block"},
        )


class SideBySideSelectorFlex(wcc.FlexBox):
    def __init__(
        self,
        tab,
        get_uuid: Callable,
        selector: str,
        link: bool = False,
        view_data: list = None,
        dropdown=False,
    ):

        super().__init__(
            children=[
                html.Div(
                    style={
                        "flex": 1,
                        "minWidth": "20px",
                        "display": "none" if link and idx != 0 else "block",
                    },
                    children=dropdown_vs_select(
                        value=data["value"],
                        options=data["options"],
                        component_id={
                            "view": idx,
                            "id": get_uuid(LayoutElements.COLORSELECTIONS)
                            if selector in ["colormap", "color_range"]
                            else get_uuid(LayoutElements.SELECTIONS),
                            "tab": tab,
                            "selector": selector,
                        },
                        multi=data.get("multi", False),
                        dropdown=dropdown,
                    )
                    if selector != "color_range"
                    else color_range_selection_layout(
                        tab,
                        get_uuid,
                        value=data["value"],
                        value_range=data["range"],
                        step=data["step"],
                        view_idx=idx,
                    ),
                )
                for idx, data in enumerate(view_data)
            ]
        )


class ViewSelector(html.Div):
    def __init__(self, tab, get_uuid: Callable):

        children = [
            html.Div(
                [
                    "Number of views",
                    html.Div(
                        dcc.Input(
                            id={"id": get_uuid(LayoutElements.VIEWS), "tab": tab},
                            type="number",
                            min=1,
                            max=9,
                            step=1,
                            value=DefaultSettings.NUMBER_OF_VIEWS.get(tab, 1),
                        ),
                        style={"float": "right"},
                    ),
                ],
                style={
                    "display": "none"
                    if tab in DefaultSettings.NUMBER_OF_VIEWS
                    else "block"
                },
            ),
            html.Div(
                wcc.Dropdown(
                    label="Create map for each:",
                    id={"id": get_uuid(LayoutElements.MULTI), "tab": tab},
                    options=[
                        {"label": LayoutLabels.NAME, "value": "name"},
                        {"label": LayoutLabels.DATE, "value": "date"},
                        {"label": LayoutLabels.ENSEMBLE, "value": "ensemble"},
                        {"label": LayoutLabels.ATTRIBUTE, "value": "attribute"},
                        {"label": LayoutLabels.REALIZATIONS, "value": "realizations"},
                    ],
                    value="name" if tab == Tabs.SPLIT else None,
                    clearable=False,
                ),
                style={
                    "margin-bottom": "10px",
                    "display": "block" if tab == Tabs.SPLIT else "none",
                },
            ),
            html.Div(
                [
                    "Views in row (optional)",
                    html.Div(
                        dcc.Input(
                            id={
                                "id": get_uuid(LayoutElements.VIEW_COLUMNS),
                                "tab": tab,
                            },
                            type="number",
                            min=1,
                            max=9,
                            step=1,
                            value=DefaultSettings.VIEWS_IN_ROW.get(tab),
                        ),
                        style={"float": "right"},
                    ),
                ]
            ),
        ]

        super().__init__(style={"font-size": "15px"}, children=children)


class MapSelector(html.Div):
    def __init__(
        self,
        tab,
        get_uuid: Callable,
        selector,
        label,
        open_details=True,
        info_text=None,
    ):
        super().__init__(
            style={
                "display": "none"
                if selector in DefaultSettings.SELECTOR_DEFAULTS.get(tab, {})
                else "block"
            },
            children=wcc.Selectors(
                label=label,
                open_details=open_details,
                children=[
                    wcc.Label(info_text) if info_text is not None else (),
                    LinkCheckBox(tab, get_uuid, selector=selector),
                    html.Div(
                        id={
                            "id": get_uuid(LayoutElements.WRAPPER),
                            "tab": tab,
                            "selector": selector,
                        },
                    ),
                ],
            ),
        )


class WellsSelector(html.Div):
    def __init__(self, tab, get_uuid: Callable, well_set_model):
        value = options = (
            well_set_model.well_names if well_set_model is not None else []
        )
        super().__init__(
            style={"display": "none" if well_set_model is None else "block"},
            children=wcc.Selectors(
                label=LayoutLabels.WELLS,
                open_details=False,
                children=dropdown_vs_select(
                    value=value,
                    options=options,
                    component_id={"id": get_uuid(LayoutElements.WELLS), "tab": tab},
                    multi=True,
                ),
            ),
        )


class RealizationSelector(MapSelector):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            tab,
            get_uuid=get_uuid,
            selector="realizations",
            label=LayoutLabels.REALIZATIONS,
            open_details=False,
            info_text=(
                "Single selection or subset "
                "for statistics dependent on aggregation mode."
            ),
        )


class FaultPolygonsSelector(wcc.Selectors):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            label=LayoutLabels.FAULTPOLYGONS,
            open_details=False,
            children=[
                wcc.Checklist(
                    id=get_uuid(LayoutElements.FAULTPOLYGONS),
                    options=[
                        {
                            "label": LayoutLabels.FAULTPOLYGONS_OPTIONS,
                            "value": LayoutLabels.FAULTPOLYGONS_OPTIONS,
                        }
                    ],
                    value=LayoutLabels.FAULTPOLYGONS_OPTIONS,
                )
            ],
        )


class SurfaceColorSelector(wcc.Selectors):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            label=LayoutLabels.COLORMAP_WRAPPER,
            open_details=False,
            children=[
                html.Div(
                    style={"margin-bottom": "10px"},
                    children=[
                        LinkCheckBox(tab, get_uuid, selector),
                        html.Div(
                            id={
                                "id": get_uuid(LayoutElements.COLORWRAPPER),
                                "tab": tab,
                                "selector": selector,
                            }
                        ),
                    ],
                )
                for selector in ["colormap", "color_range"]
            ],
        )


def dropdown_vs_select(value, options, component_id, dropdown=False, multi=False):
    if dropdown:
        if isinstance(value, list) and not multi:
            value = value[0]
        return wcc.Dropdown(
            id=component_id,
            options=[{"label": opt, "value": opt} for opt in options],
            value=value,
            clearable=False,
            multi=multi,
        )
    return wcc.SelectWithLabel(
        id=component_id,
        options=[{"label": opt, "value": opt} for opt in options],
        size=5,
        value=value,
        multi=multi,
    )


def color_range_selection_layout(tab, get_uuid, value, value_range, step, view_idx):
    return html.Div(
        children=[
            f"{LayoutLabels.COLORMAP_RANGE}",
            wcc.RangeSlider(
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.COLORSELECTIONS),
                    "selector": "color_range",
                    "tab": tab,
                },
                tooltip={"placement": "bottomLeft"},
                min=value_range[0],
                max=value_range[1],
                step=step,
                marks={str(value): {"label": f"{value:.2f}"} for value in value_range},
                value=value,
            ),
            wcc.Checklist(
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.COLORSELECTIONS),
                    "selector": "colormap_keep_range",
                    "tab": tab,
                },
                options=[
                    {
                        "label": LayoutLabels.COLORMAP_KEEP_RANGE,
                        "value": LayoutLabels.COLORMAP_KEEP_RANGE,
                    }
                ],
                value=[],
            ),
            html.Button(
                children=LayoutLabels.RANGE_RESET,
                style=LayoutStyle.RESET_BUTTON,
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.RANGE_RESET),
                    "tab": tab,
                },
            ),
        ]
    )


def update_map_layers(views, well_set_model):
    layers = []
    for idx in range(views):
        layers.extend(
            list(
                filter(
                    None,
                    [
                        ColormapLayer(uuid=f"{LayoutElements.COLORMAP_LAYER}-{idx}"),
                        Hillshading2DLayer(
                            uuid=f"{LayoutElements.HILLSHADING_LAYER}-{idx}"
                        ),
                        well_set_model
                        and WellsLayer(uuid=f"{LayoutElements.WELLS_LAYER}-{idx}"),
                    ],
                )
            )
        )

    return layers
