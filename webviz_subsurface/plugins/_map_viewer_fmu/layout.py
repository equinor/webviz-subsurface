from enum import Enum, auto, unique
from typing import Callable, List, Dict, Any, Optional
import math
import webviz_core_components as wcc
from dash import dcc, html
from pydeck import Layer
from pydeck.types import String

from webviz_subsurface._components.deckgl_map import DeckGLMap  # type: ignore
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    DrawingLayer,
    Hillshading2DLayer,
    WellsLayer,
)

from webviz_subsurface._models import WellSetModel

from .utils.formatting import format_date


@unique
class LayoutElements(str, Enum):
    """Contains all ids used in plugin. Note that some id's are
    used as combinations of LEFT/RIGHT_VIEW together with other elements to
    support pattern matching callbacks."""

    MAINVIEW = auto()
    SELECTED_DATA = auto()
    SELECTIONS = auto()
    LINK = auto()
    WELLS = auto()
    LOG = auto()
    VIEWS = auto()
    DECKGLMAP = auto()
    COLORMAP_RESET_RANGE = auto()
    STORED_COLOR_SETTINGS = auto()
    FAULTPOLYGONS = auto()
    WRAPPER = auto()
    RESET_BUTTOM_CLICK = auto()


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

    VIEWHEIGHT = 90

    SIDEBAR = {"flex": 1, "height": "90vh"}
    MAINVIEW = {"flex": 3, "height": "90vh"}


class FullScreen(wcc.WebvizPluginPlaceholder):
    def __init__(self, children: List[Any]) -> None:
        super().__init__(buttons=["expand"], children=children)


def main_layout(
    get_uuid: Callable,
    well_set_model: Optional[WellSetModel],
    show_fault_polygons: bool = True,
) -> None:

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
                            DataStores(get_uuid=get_uuid),
                            ViewSelector(get_uuid=get_uuid),
                            *[
                                MapSelector(get_uuid, selector, label=label)
                                for selector, label in selector_labels.items()
                            ],
                            RealizationSelector(get_uuid=get_uuid),
                            well_set_model
                            and WellsSelector(
                                get_uuid=get_uuid, well_set_model=well_set_model
                            ),
                            show_fault_polygons
                            and FaultPolygonsSelector(get_uuid=get_uuid),
                            SurfaceColorSelector(get_uuid=get_uuid),
                        ],
                    )
                ),
            ),
            wcc.Frame(
                id=get_uuid(LayoutElements.MAINVIEW),
                style=LayoutStyle.MAINVIEW,
                color="white",
                highlight=False,
                children=[],
            ),
        ],
    )


class DataStores(html.Div):
    def __init__(self, get_uuid: Callable) -> None:
        super().__init__(
            children=[
                dcc.Store(id=get_uuid(LayoutElements.SELECTED_DATA)),
                dcc.Store(id=get_uuid(LayoutElements.RESET_BUTTOM_CLICK)),
                dcc.Store(id=get_uuid(LayoutElements.STORED_COLOR_SETTINGS)),
            ]
        )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, get_uuid, selector: str):
        self.id = {"id": get_uuid(LayoutElements.LINK), "selector": selector}
        self.value = None
        self.options = [{"label": LayoutLabels.LINK, "value": selector}]
        super().__init__(id=self.id, options=self.options)


class SideBySideSelectorFlex(wcc.FlexBox):
    def __init__(
        self,
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
                            "selector": selector,
                        },
                        multi=data.get("multi", False),
                    )
                    if selector != "color_range"
                    else color_range_selection_layout(
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
    def __init__(self, get_uuid: Callable):
        super().__init__(
            children=[
                "Number of views",
                html.Div(
                    dcc.Input(
                        id=get_uuid(LayoutElements.VIEWS),
                        type="number",
                        min=1,
                        max=10,
                        step=1,
                        value=1,
                    ),
                    style={"float": "right"},
                ),
            ]
        )


class MapSelector(wcc.Selectors):
    def __init__(
        self, get_uuid: Callable, selector, label, open_details=True, info_text=None
    ):
        super().__init__(
            label=label,
            open_details=open_details,
            children=[
                wcc.Label(info_text) if info_text is not None else (),
                LinkCheckBox(get_uuid, selector=selector),
                html.Div(
                    id={"id": get_uuid(LayoutElements.WRAPPER), "selector": selector}
                ),
            ],
        )


class WellsSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, well_set_model):
        super().__init__(
            label=LayoutLabels.WELLS,
            open_details=False,
            children=dropdown_vs_select(
                value=well_set_model.well_names,
                options=well_set_model.well_names,
                component_id=get_uuid(LayoutElements.WELLS),
                multi=True,
            ),
        )


class RealizationSelector(MapSelector):
    def __init__(self, get_uuid: Callable):
        super().__init__(
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
    def __init__(self, get_uuid: Callable):
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
    def __init__(self, get_uuid: Callable):
        super().__init__(
            label=LayoutLabels.COLORMAP_WRAPPER,
            open_details=False,
            children=[
                LinkCheckBox(get_uuid, selector="colormap"),
                html.Div(
                    style={"margin-top": "10px"},
                    id={"id": get_uuid(LayoutElements.WRAPPER), "selector": "colormap"},
                ),
                html.Div(
                    style={"margin-top": "10px"},
                    children=[
                        LinkCheckBox(get_uuid, selector="color_range"),
                        html.Div(
                            id={
                                "id": get_uuid(LayoutElements.WRAPPER),
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


def color_range_selection_layout(get_uuid, value, value_range, step, view_idx):
    #   number_format = ".1f" if all(val > 100 for val in value) else ".3g"
    return html.Div(
        children=[
            f"{LayoutLabels.COLORMAP_RANGE}",  #: {value[0]:{number_format}} - {value[1]:{number_format}}",
            wcc.RangeSlider(
                id={
                    "view": view_idx,
                    "id": get_uuid(LayoutElements.SELECTIONS),
                    "selector": "color_range",
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
                },
            ),
        ]
    )


def create_map_list(get_uuid, views, well_set_model):
    return [
        DeckGLMap(
            id={"id": get_uuid(LayoutElements.DECKGLMAP), "view": view},
            layers=list(
                filter(
                    None,
                    [
                        ColormapLayer(),
                        Hillshading2DLayer(),
                        well_set_model and WellsLayer(),
                    ],
                )
            ),
        )
        for view in range(views)
    ]


def create_map_matrix(figures):
    """Convert a list of figures into a matrix for display"""
    figs_in_row = min([x for x in range(20) if (x * (x + 1)) > len(figures)])
    len_of_matrix = figs_in_row * math.ceil(len(figures) / figs_in_row)

    figheigth = f"{(LayoutStyle.VIEWHEIGHT/(len_of_matrix/figs_in_row))-4}vh"

    view_matrix = []
    for i in range(0, len_of_matrix, figs_in_row):
        row_figs = (
            figures[i : i + figs_in_row]
            if len(figures) > (i + figs_in_row)
            else figures[i : len(figures)] + [None] * (len_of_matrix - len(figures))
        )
        view_matrix.append(
            wcc.FlexBox(
                children=[
                    html.Div(
                        style={"flex": 1},
                        children=[
                            wcc.Label(f"Map view {str(i+fig_idx+1)}"),
                            FullScreen(html.Div(fig, style={"height": figheigth})),
                        ]
                        if fig is not None
                        else [],
                    )
                    for fig_idx, fig in enumerate(row_figs)
                ]
            )
        )
    return html.Div(view_matrix)
