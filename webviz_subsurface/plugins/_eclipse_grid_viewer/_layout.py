from enum import Enum
from typing import Callable

import dash_vtk
import webviz_core_components as wcc
from dash import dcc, html

from ._business_logic import ExplicitStructuredGridProvider


# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    INIT_RESTART = "init-restart-select"
    PROPERTIES = "properties-select"
    DATES = "dates-select"
    Z_SCALE = "z-scale"
    GRID_COLUMNS = "grid-columns"
    GRID_ROWS = "grid-rows"
    GRID_LAYERS = "grid-layers"
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


class LayoutTitles(str, Enum):
    INIT_RESTART = "Init / Restart"
    PROPERTIES = "Property"
    DATES = "Date"
    Z_SCALE = "Z-scale"
    GRID_COLUMNS = "Grid columns"
    GRID_ROWS = "Grid rows"
    GRID_LAYERS = "Grid layers"
    SHOW_GRID_LINES = "Show grid lines"
    COLORMAP = "Color map"
    GRID_FILTERS = "Grid filters"
    COLORS = "Colors"
    PICKING = "Picking"
    ENABLE_PICKING = "Enable picking"


COLORMAPS = ["erdc_rainbow_dark", "Viridis (matplotlib)", "BuRd"]


class PROPERTYTYPE(str, Enum):
    INIT = "Init"
    RESTART = "Restart"


class LayoutStyle:
    MAIN_HEIGHT = "87vh"
    SIDEBAR = {"flex": 1, "height": "87vh"}
    VTK_VIEW = {"flex": 5, "height": "87vh"}


def plugin_main_layout(
    get_uuid: Callable, esg_provider: ExplicitStructuredGridProvider
) -> wcc.FlexBox:

    return wcc.FlexBox(
        children=[
            sidebar(get_uuid=get_uuid, esg_provider=esg_provider),
            vtk_view(get_uuid=get_uuid),
            dcc.Store(id=get_uuid(LayoutElements.STORED_CELL_INDICES_HASH)),
        ]
    )


def sidebar(
    get_uuid: Callable, esg_provider: ExplicitStructuredGridProvider
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
            wcc.Checklist(
                id=get_uuid(LayoutElements.SHOW_GRID_LINES),
                options=[LayoutTitles.SHOW_GRID_LINES],
                value=[LayoutTitles.SHOW_GRID_LINES],
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
                label=LayoutTitles.GRID_FILTERS,
                children=[
                    wcc.RangeSlider(
                        label=LayoutTitles.GRID_COLUMNS,
                        id=get_uuid(LayoutElements.GRID_COLUMNS),
                        min=esg_provider.imin,
                        max=esg_provider.imax,
                        value=[esg_provider.imin, esg_provider.imax],
                        step=1,
                        marks=None,
                        tooltip={
                            "placement": "bottom",
                            "always_visible": True,
                        },
                    ),
                    wcc.RangeSlider(
                        label=LayoutTitles.GRID_ROWS,
                        id=get_uuid(LayoutElements.GRID_ROWS),
                        min=esg_provider.jmin,
                        max=esg_provider.jmax,
                        value=[esg_provider.jmin, esg_provider.jmax],
                        step=1,
                        marks=None,
                        tooltip={
                            "placement": "bottom",
                            "always_visible": True,
                        },
                    ),
                    wcc.RangeSlider(
                        label=LayoutTitles.GRID_LAYERS,
                        id=get_uuid(LayoutElements.GRID_LAYERS),
                        min=esg_provider.kmin,
                        max=esg_provider.kmax,
                        value=[esg_provider.kmin, esg_provider.kmin],
                        step=1,
                        marks=None,
                        tooltip={
                            "placement": "bottom",
                            "always_visible": True,
                        },
                    ),
                ],
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
            wcc.Checklist(
                id=get_uuid(LayoutElements.ENABLE_PICKING),
                options=[LayoutTitles.ENABLE_PICKING],
                value=[LayoutTitles.ENABLE_PICKING],
            ),
            html.Pre(id=get_uuid(LayoutElements.SELECTED_CELL)),
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
