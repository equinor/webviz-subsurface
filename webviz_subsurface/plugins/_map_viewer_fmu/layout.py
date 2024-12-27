from enum import unique
from typing import Any, Callable, Dict, List, Union

import webviz_core_components as wcc
from dash import dcc, html
from webviz_subsurface_components import SubsurfaceViewer  # type: ignore

from webviz_subsurface._utils.enum_shim import StrEnum

from ._types import LayerNames, LayerTypes, SurfaceMode
from ._utils import create_colormap_image_string, round_to_significant


@unique
class LayoutElements(StrEnum):
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
    FIELD_OUTLINE_TOGGLE = "field-outline-toggle"
    WRAPPER = "wrapper-for-selector-component"
    COLORWRAPPER = "wrapper-for-color-selector-component"
    OPTIONS = "options"

    COLORMAP_LAYER = "deckglcolormaplayer"

    WELLS_LAYER = "deckglwelllayer"
    MAP3D_LAYER = "deckglmap3dlayer"
    FAULTPOLYGONS_LAYER = "deckglfaultpolygonslayer"
    FIELD_OUTLINE_LAYER = "deckglfieldoutlinelayer"
    REALIZATIONS_FILTER = "realization-filter-selector"
    OPTIONS_DIALOG = "options-dialog"


class LayoutLabels(StrEnum):
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
    SHOW_FIELD_OUTLINE = "Show field outline"
    SHOW_WELLS = "Show wells"
    COMMON_SELECTIONS = "Options and global filters"
    REAL_FILTER = "Realization filter"
    WELL_FILTER = "Well filter"


# pylint: disable=too-few-public-methods
class LayoutStyle:
    """CSS styling"""

    MAPHEIGHT = "87vh"
    SIDEBAR = {"flex": 1, "height": "90vh", "overflow-x": "auto"}
    MAINVIEW = {"flex": 3, "height": "90vh"}
    DISABLED = {"opacity": 0.5, "pointerEvents": "none"}
    RESET_BUTTON = {
        "marginTop": "5px",
        "width": "100%",
        "height": "20px",
        "line-height": "20px",
        "background-color": "#7393B3",
        "color": "#fff",
    }
    OPTIONS_BUTTON = {
        "marginBottom": "10px",
        "width": "100%",
        "height": "30px",
        "line-height": "30px",
        "background-color": "lightgrey",
    }


class Tabs(StrEnum):
    CUSTOM = "custom"
    STATS = "stats"
    DIFF = "diff"
    SPLIT = "split"


class TabsLabels(StrEnum):
    CUSTOM = "Custom view"
    STATS = "Map statistics"
    DIFF = "Difference between two maps"
    SPLIT = "Maps per selector"


class MapSelector(StrEnum):
    ENSEMBLE = "ensemble"
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATE = "date"
    MODE = "mode"
    REALIZATIONS = "realizations"


class ColorSelector(StrEnum):
    COLORMAP = "colormap"
    COLOR_RANGE = "color_range"


# pylint: disable=too-few-public-methods
class DefaultSettings:
    NUMBER_OF_VIEWS = {Tabs.STATS: 4, Tabs.DIFF: 2, Tabs.SPLIT: 1}
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
    realizations: List[int],
    color_tables: List[Dict],
    show_fault_polygons: bool = True,
    show_field_outline: bool = False,
    render_surfaces_as_images: bool = True,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Tabs(
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
                                    children=[
                                        DataStores(tab, get_uuid),
                                        OpenDialogButton(tab, get_uuid),
                                        NumberOfViewsSelector(tab, get_uuid),
                                        MultiSelectorSelector(tab, get_uuid),
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
                                    ],
                                ),
                                wcc.Frame(
                                    id=get_uuid(LayoutElements.MAINVIEW),
                                    style=LayoutStyle.MAINVIEW,
                                    color="white",
                                    highlight=False,
                                    children=MapViewLayout(
                                        tab,
                                        get_uuid,
                                        color_tables=color_tables,
                                        render_surfaces_as_images=render_surfaces_as_images,
                                    ),
                                ),
                            ]
                        ),
                    )
                    for tab in Tabs
                ],
            ),
            DialogLayout(
                get_uuid,
                show_fault_polygons,
                show_field_outline,
                well_names,
                realizations,
            ),
        ]
    )


class OpenDialogButton(html.Button):
    def __init__(self, tab: Tabs, get_uuid: Callable) -> None:
        super().__init__(
            children=LayoutLabels.COMMON_SELECTIONS,
            id={"id": get_uuid("Button"), "tab": tab},
            style=LayoutStyle.OPTIONS_BUTTON,
        )


class MapViewLayout(FullScreen):
    """Layout for the main view containing the map"""

    def __init__(
        self,
        tab: Tabs,
        get_uuid: Callable,
        color_tables: List[Dict],
        render_surfaces_as_images: bool,
    ) -> None:
        super().__init__(
            children=html.Div(
                SubsurfaceViewer(
                    id={"id": get_uuid(LayoutElements.DECKGLMAP), "tab": tab},
                    layers=update_map_layers(1, render_surfaces_as_images),
                    colorTables=color_tables,
                ),
                style={"height": LayoutStyle.MAPHEIGHT},
            ),
        )


class DataStores(html.Div):
    """Layout for the options in the sidebar"""

    def __init__(self, tab: Tabs, get_uuid: Callable) -> None:
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


class DialogLayout(wcc.Dialog):
    """Layout for the options and filters dialog"""

    def __init__(
        self,
        get_uuid: Callable,
        show_fault_polygons: bool,
        show_field_outline: bool,
        well_names: List[str],
        realizations: List[int],
    ) -> None:
        checklist_options = []
        checklist_values = []
        if show_fault_polygons:
            checklist_options.append(LayoutLabels.SHOW_FAULTPOLYGONS)
            checklist_values.append(LayoutLabels.SHOW_FAULTPOLYGONS)

        if show_field_outline:
            checklist_options.append(LayoutLabels.SHOW_FIELD_OUTLINE)
            checklist_values.append(LayoutLabels.SHOW_FIELD_OUTLINE)

        if well_names:
            checklist_options.append(LayoutLabels.SHOW_WELLS)
            checklist_values.append(LayoutLabels.SHOW_FAULTPOLYGONS)

        super().__init__(
            title=LayoutLabels.COMMON_SELECTIONS,
            id=get_uuid(LayoutElements.OPTIONS_DIALOG),
            draggable=True,
            open=False,
            children=[
                ViewsInRowSelector(get_uuid),
                wcc.Checklist(
                    id=get_uuid(LayoutElements.OPTIONS),
                    options=[{"label": opt, "value": opt} for opt in checklist_options],
                    value=checklist_values,
                ),
                wcc.FlexBox(
                    children=[
                        html.Div(
                            style={
                                "flex": 3,
                                "minWidth": "20px",
                                "display": "block" if well_names else "none",
                            },
                            children=WellFilter(get_uuid, well_names),
                        ),
                        html.Div(
                            RealizationFilter(get_uuid, realizations),
                            style={"flex": 2, "minWidth": "20px"},
                        ),
                    ],
                    style={"width": "20vw"},
                ),
            ],
        )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, tab: Tabs, get_uuid: Callable, selector: str) -> None:
        clicked = selector in DefaultSettings.LINKED_SELECTORS.get(tab, [])
        super().__init__(
            id={
                "id": (
                    get_uuid(LayoutElements.LINK)
                    if selector not in ["color_range", "colormap"]
                    else get_uuid(LayoutElements.COLORLINK)
                ),
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
        tab: str,
        get_uuid: Callable,
        view_data: List[dict],
        selector: str,
        link: bool = False,
        dropdown: bool = False,
    ) -> None:
        children = []
        for idx, data in enumerate(view_data):
            selection_children = dropdown_vs_select(
                value=data["value"],
                options=data["options"],
                component_id={
                    "view": idx,
                    "id": get_uuid(LayoutElements.SELECTIONS),
                    "tab": tab,
                    "selector": selector,
                },
                multi=data.get("multi", False),
                dropdown=dropdown,
            )

            children.append(
                html.Div(
                    style={
                        "flex": 1,
                        "minWidth": "33%",
                        "display": "none" if link and idx != 0 else "block",
                        **(LayoutStyle.DISABLED if data.get("disabled", False) else {}),
                    },
                    children=selection_children,
                )
            )
        super().__init__(
            style={"flex-wrap": "nowrap"},
            children=children,
        )


class SideBySideColorSelectorFlex(wcc.FlexBox):
    def __init__(
        self,
        tab: str,
        get_uuid: Callable,
        view_data: List[dict],
        selector: str,
        color_tables: List[Dict],
        link: bool = False,
    ) -> None:
        children = []
        for idx, data in enumerate(view_data):
            if selector == "color_range":
                selection_children = color_range_selection_layout(
                    tab,
                    get_uuid,
                    value=data["value"],
                    value_range=data["range"],
                    step=data["step"],
                    view_idx=idx,
                )

            elif selector == "colormap":
                selection_children = colormap_dropdown(
                    value=data["value"],
                    options=data["options"],
                    component_id={
                        "view": idx,
                        "id": get_uuid(LayoutElements.COLORSELECTIONS),
                        "tab": tab,
                        "selector": selector,
                    },
                    color_tables=color_tables,
                )

            children.append(
                html.Div(
                    style={
                        "flex": 1,
                        "minWidth": "33%",
                        "display": "none" if link and idx != 0 else "block",
                        **(LayoutStyle.DISABLED if data.get("disabled", False) else {}),
                    },
                    children=selection_children,
                )
            )
        super().__init__(
            style={"flex-wrap": "nowrap"},
            children=children,
        )


class MultiSelectorSelector(html.Div):
    def __init__(self, tab: Tabs, get_uuid: Callable) -> None:
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
    def __init__(self, tab: Tabs, get_uuid: Callable) -> None:
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
    def __init__(self, get_uuid: Callable) -> None:
        super().__init__(
            children=[
                "Views in row (optional)",
                html.Div(
                    dcc.Input(
                        id=get_uuid(LayoutElements.VIEW_COLUMNS),
                        type="number",
                        min=1,
                        max=9,
                        step=1,
                    ),
                    style={"float": "right"},
                ),
            ]
        )


class RealizationFilter(wcc.SelectWithLabel):
    def __init__(self, get_uuid: Callable, realizations: List[int]) -> None:
        super().__init__(
            label=LayoutLabels.REAL_FILTER,
            id=get_uuid(LayoutElements.REALIZATIONS_FILTER),
            options=[{"label": i, "value": i} for i in realizations],
            value=realizations,
            size=min(20, len(realizations)),
        )


class WellFilter(html.Div):
    def __init__(self, get_uuid: Callable, well_names: List[str]) -> None:
        super().__init__(
            style={"display": "block" if well_names else "none"},
            children=wcc.SelectWithLabel(
                label=LayoutLabels.WELL_FILTER,
                id=get_uuid(LayoutElements.WELLS),
                options=[{"label": i, "value": i} for i in well_names],
                value=well_names,
                size=min(20, len(well_names)),
            ),
        )


class MapSelectorLayout(html.Div):
    def __init__(
        self,
        tab: Tabs,
        get_uuid: Callable,
        selector: MapSelector,
        label: str,
    ) -> None:
        super().__init__(
            style={
                "display": (
                    "none"
                    if tab == Tabs.STATS and selector == MapSelector.MODE
                    else "block"
                )
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
    def __init__(self, tab: Tabs, get_uuid: Callable) -> None:
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


def color_range_selection_layout(
    tab: str,
    get_uuid: Callable,
    value: List[float],
    value_range: List[float],
    step: float,
    view_idx: int,
) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                style={"display": "none"},
                children=wcc.RangeSlider(
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
                    marks={
                        str(value): {"label": f"{value:.2f}"} for value in value_range
                    },
                    value=value,
                ),
            ),
            html.Div(
                style={"display": "block"},
                children=[
                    html.B("Min value"),
                    html.Div(
                        children=[
                            dcc.Input(
                                id={
                                    "view": view_idx,
                                    "id": get_uuid("color-input-min"),
                                    "tab": tab,
                                },
                                value=round_to_significant(value[0]),
                                type="number",
                                style={
                                    "width": "90%",
                                    "float": "left",
                                    "margin-right": "5px",
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        style={"fontSize": "0.7em"},
                        children=f"({round_to_significant(value_range[0])})",
                    ),
                    html.B("Max value"),
                    html.Div(
                        children=[
                            dcc.Input(
                                id={
                                    "view": view_idx,
                                    "id": get_uuid("color-input-max"),
                                    "tab": tab,
                                },
                                value=round_to_significant(value[1]),
                                type="number",
                                style={
                                    "width": "90%",
                                    "float": "left",
                                    "margin-right": "5px",
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        style={"fontSize": "0.7em"},
                        children=f"({round_to_significant(value_range[1])})",
                    ),
                ],
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


def dropdown_vs_select(
    value: Union[List[str], str],
    options: List[str],
    component_id: dict,
    dropdown: bool = False,
    multi: bool = False,
) -> Union[wcc.Dropdown, wcc.SelectWithLabel]:
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


def colormap_dropdown(
    value: Union[List[str], str],
    options: List,
    component_id: dict,
    color_tables: List[Dict],
) -> Union[wcc.Dropdown, wcc.SelectWithLabel]:
    options = []
    for color_table in color_tables:
        label = html.Div(
            [
                html.Img(
                    src=create_colormap_image_string(color_table["colors"], width=50),
                    style={
                        "height": "20px",
                        "width": "50px",
                    },
                ),
                html.Label(color_table["name"], style={"marginLeft": "2px"}),
            ]
        )

        options.append({"label": label, "value": color_table["name"]})
    return wcc.Dropdown(
        id=component_id,
        options=options,
        value=value[0] if isinstance(value, list) else value,
        clearable=False,
    )


def update_map_layers(
    views: int,
    render_surfaces_as_images: bool,
    include_well_layer: bool = True,
    include_faultpolygon_layer: bool = True,
    visible_well_layer: bool = True,
    visible_fault_polygons_layer: bool = True,
) -> List[dict]:
    layers: List[Dict] = []
    for idx in range(views):
        if render_surfaces_as_images:
            layers.append(
                {
                    "@@type": LayerTypes.COLORMAP,
                    "id": f"{LayoutElements.COLORMAP_LAYER}-{idx}",
                }
            )
        if include_faultpolygon_layer:
            layers.append(
                {
                    "@@type": LayerTypes.FAULTPOLYGONS,
                    "name": LayerNames.FAULTPOLYGONS,
                    "id": f"{LayoutElements.FAULTPOLYGONS_LAYER}-{idx}",
                    "visible": visible_fault_polygons_layer,
                    "parameters": {"depthTest": False},
                }
            )
        layers.append(
            {
                "@@type": LayerTypes.FIELD_OUTLINE,
                "id": f"{LayoutElements.FIELD_OUTLINE_LAYER}-{idx}",
                "data": {"type": "FeatureCollection", "features": []},
            }
        )
        if include_well_layer:
            layers.append(
                {
                    "@@type": LayerTypes.WELLTOPSLAYER,
                    "name": LayerNames.WELLTOPSLAYER,
                    "id": f"{LayoutElements.WELLS_LAYER}-{idx}",
                    "data": {"type": "FeatureCollection", "features": []},
                    "visible": visible_well_layer,
                    "getText": "@@=properties.attribute",
                    "getTextSize": 12,
                    "getTextAnchor": "start",
                    "pointType": "circle+text",
                    "lineWidthMinPixels": 2,
                    "pointRadiusMinPixels": 2,
                    "pickable": True,
                    "parameters": {"depthTest": False},
                }
            )
    return layers
