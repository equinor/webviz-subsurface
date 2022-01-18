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

    TEST = auto()
    MAINVIEW = auto()
    SELECTED_DATA = auto()
    SELECTIONS = auto()
    LINK = auto()
    WELLS = auto()
    LOG = auto()
    VIEWS = auto()
    VIEW_COLUMNS = auto()
    DECKGLMAP = auto()
    COLORMAP_RESET_RANGE = auto()
    STORED_COLOR_SETTINGS = auto()
    FAULTPOLYGONS = auto()
    WRAPPER = auto()
    RESET_BUTTOM_CLICK = auto()

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
    COLORMAP_RESET_RANGE = "Reset"
    COLORMAP_KEEP_RANGE_OPTIONS = "Lock range"
    LINK = "🔗 Link"
    FAULTPOLYGONS = "Fault polygons"
    FAULTPOLYGONS_OPTIONS = "Show fault polygons"


class LayoutStyle:
    """CSS styling"""

    MAPHEIGHT = "87vh"
    SIDEBAR = {"flex": 1, "height": "90vh"}
    MAINVIEW = {"flex": 3, "height": "90vh"}


class Tabs(str, Enum):
    CUSTOM = "custom"
    STATS = "stats"
    DIFF = "diff"
    SPLIT = "split"


class TabsLabels(str, Enum):
    CUSTOM = "Custom view"
    STATS = "Map statistics"
    DIFF = "Difference between two maps"
    SPLIT = ("Maps per name/time",)


class DefaultSettings:

    NUMBER_OF_VIEWS = {Tabs.STATS: 4, Tabs.DIFF: 2, Tabs.SPLIT: 1}
    LINKED_SELECTORS = {
        Tabs.STATS: ["ensemble", "attribute", "name", "date"],
        Tabs.SPLIT: ["ensemble", "attribute", "name", "date", "mode", "realizations"],
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
                                if not selector
                                in DefaultSettings.SELECTOR_DEFAULTS.get(tab, {})
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
                                layers=update_map_layers(9, well_set_model),
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
                    id={"id": get_uuid(LayoutElements.RESET_BUTTOM_CLICK), "tab": tab}
                ),
                dcc.Store(
                    id={
                        "id": get_uuid(LayoutElements.STORED_COLOR_SETTINGS),
                        "tab": tab,
                    }
                ),
                dcc.Store(id={"id": get_uuid(LayoutElements.TEST), "tab": tab}),
            ]
        )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, tab, get_uuid, selector: str, clicked=False):
        self.id = {
            "id": get_uuid(LayoutElements.LINK),
            "tab": tab,
            "selector": selector,
        }
        self.value = [selector] if clicked else []
        self.options = [{"label": LayoutLabels.LINK, "value": selector}]
        self.style = {"display": "none" if clicked else "block"}
        super().__init__(
            id=self.id, options=self.options, value=self.value, style=self.style
        )


class SideBySideSelectorFlex(wcc.FlexBox):
    def __init__(
        self,
        tab,
        get_uuid: Callable,
        selector: str,
        link: bool = False,
        view_data: list = None,
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
                            "id": get_uuid(LayoutElements.SELECTIONS),
                            "tab": tab,
                            "selector": selector,
                        },
                        multi=data.get("multi", False),
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

        super().__init__(
            style={"font-size": "15px"},
            children=[
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
                            ),
                            style={"float": "right"},
                        ),
                    ]
                ),
            ],
        )


class MapSelector(wcc.Selectors):
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
            label=label,
            open_details=open_details,
            children=[
                wcc.Label(info_text) if info_text is not None else (),
                LinkCheckBox(
                    tab,
                    get_uuid,
                    selector=selector,
                    clicked=selector in DefaultSettings.LINKED_SELECTORS.get(tab, []),
                ),
                html.Div(
                    id={
                        "id": get_uuid(LayoutElements.WRAPPER),
                        "tab": tab,
                        "selector": selector,
                    },
                ),
            ],
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
                LinkCheckBox(tab, get_uuid, selector="colormap"),
                html.Div(
                    style={"margin-top": "10px"},
                    id={
                        "id": get_uuid(LayoutElements.WRAPPER),
                        "tab": tab,
                        "selector": "colormap",
                    },
                ),
                html.Div(
                    style={"margin-top": "10px"},
                    children=[
                        LinkCheckBox(tab, get_uuid, selector="color_range"),
                        html.Div(
                            id={
                                "id": get_uuid(LayoutElements.WRAPPER),
                                "tab": tab,
                                "selector": "color_range",
                            }
                        ),
                    ],
                ),
            ],
        )


def dropdown_vs_select(value, options, component_id, multi=False):
    if isinstance(value, str):
        return wcc.Dropdown(
            id=component_id,
            options=[{"label": opt, "value": opt} for opt in options],
            value=value,
            clearable=False,
        )
    return wcc.SelectWithLabel(
        id=component_id,
        options=[{"label": opt, "value": opt} for opt in options],
        size=5,
        value=value,
        multi=multi,
    )


def color_range_selection_layout(tab, get_uuid, value, value_range, step, view_idx):
    #   number_format = ".1f" if all(val > 100 for val in value) else ".3g"
    return html.Div(
        children=[
            f"{LayoutLabels.COLORMAP_RANGE}",  #: {value[0]:{number_format}} - {value[1]:{number_format}}",
            wcc.RangeSlider(
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.SELECTIONS),
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
                    "id": get_uuid(LayoutElements.SELECTIONS),
                    "selector": "colormap_keep_range",
                    "tab": tab,
                },
                options=[
                    {
                        "label": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                        "value": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                    }
                ],
                value=[],
            ),
            html.Button(
                children=LayoutLabels.COLORMAP_RESET_RANGE,
                style={
                    "marginTop": "5px",
                    "width": "100%",
                    "height": "20px",
                    "line-height": "20px",
                    "background-color": "#7393B3",
                    "color": "#fff",
                },
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.COLORMAP_RESET_RANGE),
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
