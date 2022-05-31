from enum import Enum
from typing import Callable, Optional, List

import webviz_vtk
import webviz_core_components as wcc
from dash import dcc, html

from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProvider,
    CellFilter,
)
from webviz_subsurface._providers.well_provider import WellProvider

# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    REALIZATIONS = "realization"
    INIT_RESTART = "init-restart-select"
    PROPERTIES = "properties-select"
    DATES = "dates-select"
    WELL_SELECT = "well-select"
    Z_SCALE = "z-scale"
    VTK_VIEW = "vtk-view"
    VTK_INTERSECT_VIEW = "vtk-intersect-view"
    VTK_GRID_REPRESENTATION = "vtk-grid-representation"
    VTK_GRID_POLYDATA = "vtk-grid-polydata"
    VTK_GRID_CELLDATA = "vtk-grid-celldata"
    VTK_WELL_INTERSECT_REPRESENTATION = "vtk-well-intersect-representation"
    VTK_WELL_INTERSECT_POLYDATA = "vtk-well-intersect-polydata"
    VTK_WELL_INTERSECT_CELL_DATA = "vtk-well-intersect-celldata"
    VTK_WELL_PATH_REPRESENTATION = "vtk-well-path-representation"
    VTK_WELL_PATH_POLYDATA = "vtk-well-path-polydata"
    VTK_WELL_2D_INTERSECT_REPRESENTATION = "vtk-well-2d-intersect-representation"
    VTK_WELL_2D_INTERSECT_POLYDATA = "vtk-well-2d-intersect-polydata"
    VTK_WELL_2D_INTERSECT_CELL_DATA = "vtk-well-2d-intersect-celldata"
    VTK_WELL_PATH_2D_REPRESENTATION = "vtk-well-2d-path-representation"
    VTK_WELL_PATH_2D_POLYDATA = "vtk-well-2d-path-polydata"
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
    REALIZATIONS = "Realization"
    INIT_RESTART = "Init / Restart"
    PROPERTIES = "Property"
    DATES = "Date"
    WELL_SELECT = "Well"
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
    VTK_VIEW = {"height": "40vh", "marginBottom": "10px"}


def plugin_main_layout(
    get_uuid: Callable, grid_provider: EnsembleGridProvider, well_names: List[str]
) -> wcc.FlexBox:
    initial_grid = grid_provider.get_3dgrid(grid_provider.realizations()[0])
    grid_dimensions = CellFilter(
        i_min=0,
        j_min=0,
        k_min=0,
        i_max=initial_grid.dimensions[0] - 1,
        j_max=initial_grid.dimensions[1] - 1,
        k_max=initial_grid.dimensions[2] - 1,
    )
    return wcc.FlexBox(
        children=[
            sidebar(
                get_uuid=get_uuid,
                grid_dimensions=grid_dimensions,
                grid_provider=grid_provider,
                well_names=well_names,
            ),
            html.Div(
                style={"flex": "5"},
                children=[
                    vtk_3d_view(get_uuid=get_uuid),
                    vtk_intersect_view(get_uuid=get_uuid),
                ],
            ),
            dcc.Store(id=get_uuid(LayoutElements.STORED_CELL_INDICES_HASH)),
            dcc.Store(
                id=get_uuid(LayoutElements.GRID_RANGE_STORE),
                data=[
                    [grid_dimensions.i_min, grid_dimensions.i_max],
                    [grid_dimensions.j_min, grid_dimensions.j_max],
                    [grid_dimensions.k_min, grid_dimensions.k_min],
                ],
            ),
        ]
    )


def sidebar(
    get_uuid: Callable,
    grid_dimensions: CellFilter,
    grid_provider: EnsembleGridProvider,
    well_names: List[str],
) -> wcc.Frame:

    realizations = grid_provider.realizations()
    property_options = []
    property_value = None

    if grid_provider.static_property_names():
        property_options.append(
            {"label": PROPERTYTYPE.INIT, "value": PROPERTYTYPE.INIT}
        )
        property_value = PROPERTYTYPE.INIT

    if grid_provider.dynamic_property_names():
        property_options.append(
            {"label": PROPERTYTYPE.RESTART, "value": PROPERTYTYPE.RESTART}
        )
        if property_value is None:
            property_value = PROPERTYTYPE.RESTART

    return wcc.Frame(
        style=LayoutStyle.SIDEBAR,
        children=[
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.REALIZATIONS),
                label=LayoutTitles.REALIZATIONS,
                options=[{"label": real, "value": real} for real in realizations],
                value=[realizations[0]],
                multi=False,
            ),
            wcc.RadioItems(
                label=LayoutTitles.INIT_RESTART,
                id=get_uuid(LayoutElements.INIT_RESTART),
                options=property_options,
                value=property_value,
            ),
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.PROPERTIES),
                label=LayoutTitles.PROPERTIES,
            ),
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.DATES), label=LayoutTitles.DATES
            ),
            wcc.SelectWithLabel(
                id=get_uuid(LayoutElements.WELL_SELECT),
                label=LayoutTitles.WELL_SELECT,
                multi=False,
                options=[{"value": well, "label": well} for well in well_names],
                value=[],
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
                        min_val=grid_dimensions.i_min,
                        max_val=grid_dimensions.i_max,
                        direction=GRID_DIRECTION.I,
                    ),
                    crop_widget(
                        get_uuid=get_uuid,
                        min_val=grid_dimensions.j_min,
                        max_val=grid_dimensions.j_max,
                        direction=GRID_DIRECTION.J,
                    ),
                    crop_widget(
                        get_uuid=get_uuid,
                        min_val=grid_dimensions.k_min,
                        max_val=grid_dimensions.k_max,
                        max_width=grid_dimensions.k_min,
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
            html.Pre(id=get_uuid(LayoutElements.SELECTED_CELL), children=[]),
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
                        style={"width": "50px", "height": "10px"},
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
                        style={"width": "50px", "height": "10px"},
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
                        min=1,
                        max=max_val,
                    ),
                    wcc.Slider(
                        id={
                            "id": get_uuid(LayoutElements.CROP_WIDGET),
                            "direction": direction,
                            "component": "slider",
                            "component2": "width",
                        },
                        min=1,
                        max=max_val,
                        value=max_width,
                        step=1,
                        marks=None,
                    ),
                ],
            ),
        ],
    )


def vtk_3d_view(get_uuid: Callable) -> webviz_vtk.View:
    return webviz_vtk.View(
        id=get_uuid(LayoutElements.VTK_VIEW),
        style=LayoutStyle.VTK_VIEW,
        pickingModes=["click"],
        interactorSettings=[
            {
                "button": 1,
                "action": "Zoom",
                "scrollEnabled": True,
            },
            {
                "button": 3,
                "action": "Pan",
            },
            {
                "button": 2,
                "action": "Rotate",
            },
            {
                "button": 1,
                "action": "Pan",
                "shift": True,
            },
            {
                "button": 1,
                "action": "Zoom",
                "alt": True,
            },
            {
                "button": 1,
                "action": "Roll",
                "alt": True,
                "shift": True,
            },
        ],
        children=[
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_GRID_REPRESENTATION),
                showCubeAxes=True,
                showScalarBar=True,
                children=[
                    webviz_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_GRID_POLYDATA),
                        children=[
                            webviz_vtk.CellData(
                                [
                                    webviz_vtk.DataArray(
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
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_PICK_REPRESENTATION),
                actor={"visibility": False},
                children=[
                    webviz_vtk.Algorithm(
                        id=get_uuid(LayoutElements.VTK_PICK_SPHERE),
                        vtkClass="vtkSphereSource",
                    )
                ],
            ),
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_WELL_INTERSECT_REPRESENTATION),
                actor={"visibility": True},
                children=[
                    webviz_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_WELL_INTERSECT_POLYDATA),
                        children=[
                            webviz_vtk.CellData(
                                [
                                    webviz_vtk.DataArray(
                                        id=get_uuid(
                                            LayoutElements.VTK_WELL_INTERSECT_CELL_DATA
                                        ),
                                        registration="setScalars",
                                        name="scalar",
                                    )
                                ]
                            )
                        ],
                    )
                ],
            ),
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_WELL_PATH_REPRESENTATION),
                actor={"visibility": True},
                children=[
                    webviz_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_WELL_PATH_POLYDATA),
                    )
                ],
            ),
        ],
    )


def vtk_intersect_view(get_uuid: Callable) -> webviz_vtk.View:
    return webviz_vtk.View(
        id=get_uuid(LayoutElements.VTK_INTERSECT_VIEW),
        style=LayoutStyle.VTK_VIEW,
        pickingModes=["click"],
        interactorSettings=[
            {
                "button": 1,
                "action": "Zoom",
                "scrollEnabled": True,
            },
            {
                "button": 3,
                "action": "Pan",
            },
            {
                "button": 2,
                "action": "Rotate",
            },
            {
                "button": 1,
                "action": "Pan",
                "shift": True,
            },
            {
                "button": 1,
                "action": "Zoom",
                "alt": True,
            },
            {
                "button": 1,
                "action": "Roll",
                "alt": True,
                "shift": True,
            },
        ],
        children=[
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_WELL_2D_INTERSECT_REPRESENTATION),
                actor={"visibility": True},
                property={"edgeVisibility": True},
                children=[
                    webviz_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_WELL_2D_INTERSECT_POLYDATA),
                        children=[
                            webviz_vtk.CellData(
                                [
                                    webviz_vtk.DataArray(
                                        id=get_uuid(
                                            LayoutElements.VTK_WELL_2D_INTERSECT_CELL_DATA
                                        ),
                                        registration="setScalars",
                                        name="scalar",
                                    )
                                ]
                            )
                        ],
                    )
                ],
            ),
            webviz_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_WELL_PATH_2D_REPRESENTATION),
                actor={"visibility": True},
                children=[
                    webviz_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_WELL_PATH_2D_POLYDATA),
                    )
                ],
            ),
        ],
    )
