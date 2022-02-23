from enum import Enum, auto, unique
from typing import Callable, List, Dict, Any, Optional
import json
import webviz_core_components as wcc
from dash import dcc, html


from webviz_subsurface_components import DeckGLMap  # type: ignore
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    DrawingLayer,
    Hillshading2DLayer,
    WellsLayer,
    Map3DLayer,
    FaultPolygonsLayer,
)
from ._types import SurfaceMode
from webviz_subsurface._models import WellSetModel

from .utils.formatting import format_date


@unique
class LayoutElements(str, Enum):
    """Contains all ids used in plugin. Note that some id's are
    used as combinations of LEFT/RIGHT_VIEW together with other elements to
    support pattern matching callbacks."""

    MULTI = "multiselection"
    MAINVIEW = "main-view"
    SELECTIONS = "input-selections-from-layout"
    COLORSELECTIONS = "input-color-selections-from-layout"
    STORED_COLOR_SETTINGS = "cached-color-selections"
    VIEW_DATA = "stored-combined-raw-selections"
    LINKED_VIEW_DATA = "stored-selections-after-linking-set"
    VERIFIED_VIEW_DATA = "stored-verified-selections"
    VERIFIED_VIEW_DATA_WITH_COLORS = "stored-verified-selections-with-colors"

    LINK = "link-checkbox"
    COLORLINK = "color-link-checkbox"
    WELLS = "wells-selector"
    LOG = "log-selector"
    VIEWS = "number-of-views-input"
    VIEW_COLUMNS = "number-of-views-in-column-input"
    DECKGLMAP = "deckgl-component"
    RANGE_RESET = "color-range-reset-button"
    RESET_BUTTOM_CLICK = "color-range-reset-stored-state"
    FAULTPOLYGONS = "fault-polygon-toggle"
    WRAPPER = "wrapper-for-selector-component"
    COLORWRAPPER = "wrapper-for-color-selector-component"
    OPTIONS = "options"

    COLORMAP_LAYER = "deckglcolormaplayer"
    HILLSHADING_LAYER = "deckglhillshadinglayer"
    WELLS_LAYER = "deckglwelllayer"
    MAP3D_LAYER = "deckglmap3dlayer"
    FAULTPOLYGONS_LAYER = "deckglfaultpolygonslayer"
    REALIZATIONS_FILTER = "realization-filter-selector"


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
    SHOW_FAULTPOLYGONS = "Show fault polygons"
    SHOW_WELLS = "Show wells"
    SHOW_HILLSHADING = "Hillshading"
    COMMON_SELECTIONS = "Options"
    REAL_FILTER = "Realization filter"
    WELL_FILTER = "Well filter"


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


class MapSelector(str, Enum):
    ENSEMBLE = "ensemble"
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATE = "date"
    MODE = "mode"
    REALIZATIONS = "realizations"


class ColorSelector(str, Enum):
    COLORMAP = "colormap"
    COLOR_RANGE = "color_range"


class DefaultSettings:

    NUMBER_OF_VIEWS = {Tabs.STATS: 4, Tabs.DIFF: 2, Tabs.SPLIT: 1}
    VIEWS_IN_ROW = {Tabs.DIFF: 3}
    LINKED_SELECTORS = {
        Tabs.STATS: [
            MapSelector.ENSEMBLE,
            MapSelector.ATTRIBUTE,
            MapSelector.NAME,
            MapSelector.DATE,
            ColorSelector.COLORMAP,
        ],
        Tabs.SPLIT: [
            MapSelector.ENSEMBLE,
            MapSelector.ATTRIBUTE,
            MapSelector.NAME,
            MapSelector.DATE,
            MapSelector.MODE,
            MapSelector.REALIZATIONS,
            ColorSelector.COLORMAP,
        ],
    }
    VIEW_LAYOUT_STATISTICS_TAB = [
        SurfaceMode.MEAN,
        SurfaceMode.REALIZATION,
        SurfaceMode.STDDEV,
        SurfaceMode.OBSERVED,
    ]
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
    well_names: List[str],
    realizations,
    show_fault_polygons: bool = True,
):
    return wcc.Tabs(
        id=get_uuid("tabs"),
        style={"width": "100%"},
        value=Tabs.CUSTOM,
        children=[
            wcc.Tab(
                label=TabsLabels[tab.name],
                value=tab,
                children=wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style=LayoutStyle.SIDEBAR,
                            children=TabSidebarLayout(
                                tab,
                                get_uuid,
                                well_names,
                                realizations,
                                show_fault_polygons,
                            ),
                        ),
                        wcc.Frame(
                            id=get_uuid(LayoutElements.MAINVIEW),
                            style=LayoutStyle.MAINVIEW,
                            color="white",
                            highlight=False,
                            children=MapViewLayout(tab, get_uuid, well_names),
                        ),
                    ]
                ),
            )
            for tab in Tabs
        ],
    )


class MapViewLayout(FullScreen):
    """Layout for the main view containing the map"""

    def __init__(self, tab, get_uuid, well_names):
        super().__init__(
            children=html.Div(
                DeckGLMap(
                    id={"id": get_uuid(LayoutElements.DECKGLMAP), "tab": tab},
                    layers=update_map_layers(1, bool(well_names)),
                    zoom=-4,
                ),
                style={"height": LayoutStyle.MAPHEIGHT},
            ),
        )


class DataStores(html.Div):
    """Layout for the options in the sidebar"""

    def __init__(self, tab, get_uuid):
        super().__init__(
            children=[
                dcc.Store(id={"id": get_uuid(element), "tab": tab})
                for element in [
                    LayoutElements.VERIFIED_VIEW_DATA_WITH_COLORS,
                    LayoutElements.VERIFIED_VIEW_DATA,
                    LayoutElements.LINKED_VIEW_DATA,
                    LayoutElements.VIEW_DATA,
                ]
            ]
            + [dcc.Store(id=get_uuid(LayoutElements.STORED_COLOR_SETTINGS))]
        )


class TabSidebarLayout(html.Div):
    """Class containing the layout for the individual tab"""

    def __init__(
        self,
        tab,
        get_uuid: Callable,
        well_names: List[str],
        realizations,
        show_fault_polygons: bool = True,
    ) -> None:
        super().__init__(
            children=[
                DataStores(tab, get_uuid),
                NumberOfViewsSelector(tab, get_uuid),
                MultiSelectorSelector(tab, get_uuid),
                OptionsLayout(
                    tab, get_uuid, show_fault_polygons, well_names, realizations
                ),
                html.Div(
                    [
                        MapSelectorLayout(
                            tab=tab,
                            get_uuid=get_uuid,
                            selector=selector,
                            label=LayoutLabels[selector.name],
                        )
                        for selector in MapSelector
                    ]
                ),
                SurfaceColorSelector(tab, get_uuid),
            ]
        )


class OptionsLayout(wcc.Selectors):
    """Layout for the options in the sidebar"""

    def __init__(self, tab, get_uuid, show_fault_polygons, well_names, realizations):

        checklist_options = [LayoutLabels.SHOW_HILLSHADING]
        if show_fault_polygons:
            checklist_options.append(LayoutLabels.SHOW_FAULTPOLYGONS)
        if well_names:
            checklist_options.append(LayoutLabels.SHOW_WELLS)

        super().__init__(
            label=LayoutLabels.COMMON_SELECTIONS,
            open_details=False,
            children=[
                ViewsInRowSelector(tab, get_uuid),
                wcc.Checklist(
                    id={"id": get_uuid(LayoutElements.OPTIONS), "tab": tab},
                    options=[{"label": opt, "value": opt} for opt in checklist_options],
                    value=checklist_options,
                ),
                wcc.FlexBox(
                    [
                        html.Div(
                            style={"flex": 3, "minWidth": "20px"},
                            children=WellFilter(tab, get_uuid, well_names)
                            if well_names
                            else [],
                        ),
                        html.Div(
                            RealizationFilter(tab, get_uuid, realizations),
                            style={"flex": 2, "minWidth": "20px"},
                        ),
                    ]
                ),
            ],
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


class MultiSelectorSelector(html.Div):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            style={
                "margin-bottom": "15px",
                "display": "block" if tab == Tabs.SPLIT else "none",
            },
            children=wcc.Dropdown(
                label="Create map for each:",
                id={"id": get_uuid(LayoutElements.MULTI), "tab": tab},
                options=[
                    {
                        "label": LayoutLabels[selector.name],
                        "value": selector,
                    }
                    for selector in [
                        MapSelector.NAME,
                        MapSelector.DATE,
                        MapSelector.ENSEMBLE,
                        MapSelector.ATTRIBUTE,
                        MapSelector.REALIZATIONS,
                    ]
                ],
                value=MapSelector.NAME if tab == Tabs.SPLIT else None,
                clearable=False,
            ),
        )


class NumberOfViewsSelector(html.Div):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            children=[
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
                "display": "none" if tab in DefaultSettings.NUMBER_OF_VIEWS else "block"
            },
        )


class ViewsInRowSelector(html.Div):
    def __init__(self, tab, get_uuid: Callable):
        super().__init__(
            children=[
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
        )


class RealizationFilter(wcc.SelectWithLabel):
    def __init__(self, tab, get_uuid: Callable, realizations):
        super().__init__(
            label=LayoutLabels.REAL_FILTER,
            id={"id": get_uuid(LayoutElements.REALIZATIONS_FILTER), "tab": tab},
            options=[{"label": i, "value": i} for i in realizations],
            value=realizations,
            size=min(6, len(realizations)),
        )


class WellFilter(wcc.SelectWithLabel):
    def __init__(self, tab, get_uuid: Callable, well_names):
        super().__init__(
            label=LayoutLabels.WELL_FILTER,
            id={"id": get_uuid(LayoutElements.WELLS), "tab": tab},
            options=[{"label": i, "value": i} for i in well_names],
            value=well_names,
            size=min(6, len(well_names)),
        )


class MapSelectorLayout(html.Div):
    def __init__(
        self,
        tab,
        get_uuid: Callable,
        selector,
        label,
    ):
        super().__init__(
            style={
                "display": "none"
                if tab == Tabs.STATS and selector == MapSelector.MODE
                else "block"
            },
            children=wcc.Selectors(
                label=label,
                children=[
                    LinkCheckBox(tab, get_uuid, selector=selector),
                    html.Div(
                        id={
                            "id": get_uuid(LayoutElements.WRAPPER),
                            "tab": tab,
                            "selector": selector,
                        }
                    ),
                ],
            ),
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
                for selector in ColorSelector
            ],
        )


def color_range_selection_layout(tab, get_uuid, value, value_range, step, view_idx):
    return html.Div(
        children=[
            f"{LayoutLabels.COLORMAP_RANGE}",
            wcc.RangeSlider(
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.COLORSELECTIONS),
                    "selector": ColorSelector.COLOR_RANGE,
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


def update_map_layers(
    views,
    include_well_layer=True,
    include_faultpolygon_layer=True,
    visible_well_layer=True,
    visible_fault_polygons_layer=True,
    visible_hillshading_layer=True,
):
    layers = []
    for idx in range(views):
        layers.extend(
            [
                # Map3DLayer(uuid=f"{LayoutElements.MAP3D_LAYER}-{idx}"),
                ColormapLayer(uuid=f"{LayoutElements.COLORMAP_LAYER}-{idx}"),
                Hillshading2DLayer(
                    uuid=f"{LayoutElements.HILLSHADING_LAYER}-{idx}",
                    visible=visible_hillshading_layer,
                ),
            ]
        )

        if include_faultpolygon_layer:
            layers.append(
                FaultPolygonsLayer(
                    uuid=f"{LayoutElements.FAULTPOLYGONS_LAYER}-{idx}",
                    visible=visible_fault_polygons_layer,
                )
            )
        if include_well_layer:
            layers.append(
                WellsLayer(
                    uuid=f"{LayoutElements.WELLS_LAYER}-{idx}",
                    visible=visible_well_layer,
                )
            )

    return [json.loads(layer.to_json()) for layer in layers]
