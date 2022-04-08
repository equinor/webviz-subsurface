from enum import Enum
from typing import Callable, Optional

import dash_vtk
import webviz_core_components as wcc
from dash import dcc, html

from ._explicit_structured_grid_accessor import ExplicitStructuredGridAccessor


# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    INIT_RESTART = "init-restart-select"
    PROPERTIES = "properties-select"
    DATES = "dates-select"
    Z_SCALE = "z-scale"
    VTK_VIEW = "vtk-view"
    VTK_GRID_REPRESENTATION = "vtk-grid-representation"
    VTK_GRID_POLYDATA = "vtk-grid-polydata"
    VTK_GRID_CELLDATA = "vtk-grid-celldata"
    STORED_CELL_INDICES_HASH = "stored-cell-indices-hash"
    SELECTED_CELL = "selected-cell"
    SHOW_GRID_LINES = "show-grid-lines"
    COLORMAP = "color-map"
    ENABLE_PICKING = "enable-picking"
    VTK_PICK_REPRESENTATION = "vtk-pick-representation"
    VTK_PICK_SPHERE = "vtk-pick-sphere"
    SHOW_AXES = "show-axes"
    CROP_WIDGET = "crop-widget"
    GRID_RANGE_STORE = "crop-widget-store"


class LayoutTitles(str, Enum):
    INIT_RESTART = "Init / Restart"
    PROPERTIES = "Property"
    DATES = "Date"
    Z_SCALE = "Z-scale"
    SHOW_GRID_LINES = "Show grid lines"
    COLORMAP = "Color map"
    GRID_FILTERS = "Grid filters"
    COLORS = "Colors"
    PICKING = "Picking"
    ENABLE_PICKING = "Enable readout from picked cell"
    SHOW_AXES = "Show axes"


class GRID_DIRECTION(str, Enum):
    I = "I"
    J = "J"
    K = "K"


COLORMAPS = ["erdc_rainbow_dark", "Viridis (matplotlib)", "BuRd"]


class PROPERTYTYPE(str, Enum):
    INIT = "Init"
    RESTART = "Restart"


class LayoutStyle:
    MAIN_HEIGHT = "87vh"
    SIDEBAR = {"flex": 1, "height": "87vh"}
    VTK_VIEW = {"flex": 5, "height": "87vh"}


def plugin_main_layout(
    get_uuid: Callable, esg_accessor: ExplicitStructuredGridAccessor
) -> wcc.FlexBox:

    return wcc.FlexBox(
        children=[
            sidebar(get_uuid=get_uuid, esg_accessor=esg_accessor),
            vtk_view(get_uuid=get_uuid),
            dcc.Store(id=get_uuid(LayoutElements.STORED_CELL_INDICES_HASH)),
            dcc.Store(
                id=get_uuid(LayoutElements.GRID_RANGE_STORE),
                data=[
                    [esg_accessor.imin, esg_accessor.imax],
                    [esg_accessor.jmin, esg_accessor.jmax],
                    [esg_accessor.kmin, esg_accessor.kmin],
                ],
            ),
        ]
    )


def sidebar(
    get_uuid: Callable, esg_accessor: ExplicitStructuredGridAccessor
) -> wcc.Frame:
    return wcc.Frame(
        style=LayoutStyle.SIDEBAR,
        children=[
            wcc.RadioItems(
                label=LayoutTitles.INIT_RESTART,
                id=get_uuid(LayoutElements.INIT_RESTART),
                options=[{"label": prop, "value": prop} for prop in PROPERTYTYPE],
                value=PROPERTYTYPE.INIT,
            ),
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.PROPERTIES), label=LayoutTitles.PROPERTIES
            ),
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.DATES), label=LayoutTitles.DATES
            ),
            wcc.Slider(
                label=LayoutTitles.Z_SCALE,
                id=get_uuid(LayoutElements.Z_SCALE),
                min=1,
                max=10,
                value=1,
                step=1,
            ),
            wcc.Selectors(
                label=LayoutTitles.COLORS,
                children=[
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.COLORMAP),
                        options=[
                            {"value": colormap, "label": colormap}
                            for colormap in COLORMAPS
                        ],
                        value=COLORMAPS[0],
                        clearable=False,
                    )
                ],
            ),
            wcc.Selectors(
                label="Range filters",
                children=[
                    crop_widget(
                        get_uuid=get_uuid,
                        min_val=esg_accessor.imin,
                        max_val=esg_accessor.imax,
                        direction=GRID_DIRECTION.I,
                    ),
                    crop_widget(
                        get_uuid=get_uuid,
                        min_val=esg_accessor.jmin,
                        max_val=esg_accessor.jmax,
                        direction=GRID_DIRECTION.J,
                    ),
                    crop_widget(
                        get_uuid=get_uuid,
                        min_val=esg_accessor.kmin,
                        max_val=esg_accessor.kmax,
                        max_width=esg_accessor.kmin,
                        direction=GRID_DIRECTION.K,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Options",
                children=[
                    wcc.Checklist(
                        id=get_uuid(LayoutElements.SHOW_AXES),
                        options=[LayoutTitles.SHOW_AXES],
                        value=[LayoutTitles.SHOW_AXES],
                    ),
                    wcc.Checklist(
                        id=get_uuid(LayoutElements.SHOW_GRID_LINES),
                        options=[LayoutTitles.SHOW_GRID_LINES],
                        value=[LayoutTitles.SHOW_GRID_LINES],
                    ),
                ],
            ),
            wcc.Selectors(
                label="Readout",
                children=[
                    wcc.Checklist(
                        id=get_uuid(LayoutElements.ENABLE_PICKING),
                        options=[LayoutTitles.ENABLE_PICKING],
                        value=[LayoutTitles.ENABLE_PICKING],
                    )
                ],
            ),
            html.Pre(id=get_uuid(LayoutElements.SELECTED_CELL)),
        ],
    )


def crop_widget(
    get_uuid: Callable,
    min_val: int,
    max_val: int,
    direction: str,
    max_width: Optional[int] = None,
) -> html.Div:
    max_width = max_width if max_width else max_val
    return html.Div(
        children=[
            html.Div(
                style={
                    "display": "grid",
                    "marginBotton": "0px",
                    "gridTemplateColumns": f"2fr 1fr 8fr",
                },
                children=[
                    wcc.Label(
                        children=f"{direction} Start",
                        style={
                            "fontSize": "0.7em",
                            "fontWeight": "bold",
                            "marginRight": "5px",
                        },
                    ),
                    dcc.Input(
                        style={"width": "30px", "height": "10px"},
                        id={
                            "id": get_uuid(LayoutElements.CROP_WIDGET),
                            "direction": direction,
                            "component": "input",
                            "component2": "start",
                        },
                        type="number",
                        placeholder="Min",
                        persistence=True,
                        persistence_type="session",
                        value=min_val,
                        min=min_val,
                        max=max_val,
                    ),
                    wcc.Slider(
                        id={
                            "id": get_uuid(LayoutElements.CROP_WIDGET),
                            "direction": direction,
                            "component": "slider",
                            "component2": "start",
                        },
                        min=min_val,
                        max=max_val,
                        value=min_val,
                        step=1,
                        marks=None,
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "grid",
                    "marginTop": "0px",
                    "padding": "0px",
                    "gridTemplateColumns": f"2fr 1fr 8fr",
                },
                children=[
                    wcc.Label(
                        children=f"Width",
                        style={
                            "fontSize": "0.7em",
                            "textAlign": "right",
                            "marginRight": "5px",
                        },
                    ),
                    dcc.Input(
                        style={"width": "30px", "height": "10px"},
                        id={
                            "id": get_uuid(LayoutElements.CROP_WIDGET),
                            "direction": direction,
                            "component": "input",
                            "component2": "width",
                        },
                        type="number",
                        placeholder="Min",
                        persistence=True,
                        persistence_type="session",
                        value=max_width,
                        min=min_val,
                        max=max_val,
                    ),
                    wcc.Slider(
                        id={
                            "id": get_uuid(LayoutElements.CROP_WIDGET),
                            "direction": direction,
                            "component": "slider",
                            "component2": "width",
                        },
                        min=min_val,
                        max=max_val,
                        value=max_width,
                        step=1,
                        marks=None,
                    ),
                ],
            ),
        ],
    )


def vtk_view(get_uuid: Callable) -> dash_vtk.View:
    return dash_vtk.View(
        id=get_uuid(LayoutElements.VTK_VIEW),
        style=LayoutStyle.VTK_VIEW,
        pickingModes=["click"],
        children=[
            dash_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_GRID_REPRESENTATION),
                showCubeAxes=True,
                showScalarBar=True,
                children=[
                    dash_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_GRID_POLYDATA),
                        children=[
                            dash_vtk.CellData(
                                [
                                    dash_vtk.DataArray(
                                        id=get_uuid(LayoutElements.VTK_GRID_CELLDATA),
                                        registration="setScalars",
                                        name="scalar",
                                    )
                                ]
                            )
                        ],
                    )
                ],
                property={"edgeVisibility": True},
            ),
            dash_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_PICK_REPRESENTATION),
                actor={"visibility": False},
                children=[
                    dash_vtk.Algorithm(
                        id=get_uuid(LayoutElements.VTK_PICK_SPHERE),
                        vtkClass="vtkSphereSource",
                    )
                ],
            ),
        ],
    )
