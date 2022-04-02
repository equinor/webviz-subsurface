from enum import Enum
from typing import Callable

import dash_vtk
import webviz_core_components as wcc

from ._business_logic import ExplicitStructuredGridProvider


# pylint: disable = too-few-public-methods
class LayoutElements(str, Enum):
    INIT_RESTART = "init-restart-select"
    PROPERTIES = "properties-select"
    DATES = "dates-select"
    VTK_VIEW = "vtk-view"
    VTK_GRID_REPRESENTATION = "vtk-grid-representation"
    VTK_GRID_POLYDATA = "vtk-grid-polydata"
    VTK_GRID_CELLDATA = "vtk-grid-celldata"


class LayoutTitles(str, Enum):
    INIT_RESTART = "Init / Restart"
    PROPERTIES = "Property"
    DATES = "Date"


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
            sidebar(get_uuid=get_uuid),
            vtk_view(get_uuid=get_uuid, esg_provider=esg_provider),
        ]
    )


def sidebar(get_uuid: Callable) -> wcc.Frame:
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
        ],
    )


def vtk_view(
    get_uuid: Callable, esg_provider: ExplicitStructuredGridProvider
) -> dash_vtk.View:
    return dash_vtk.View(
        id=get_uuid(LayoutElements.VTK_VIEW),
        style=LayoutStyle.VTK_VIEW,
        children=[
            dash_vtk.GeometryRepresentation(
                id=get_uuid(LayoutElements.VTK_GRID_REPRESENTATION),
                children=[
                    dash_vtk.PolyData(
                        id=get_uuid(LayoutElements.VTK_GRID_POLYDATA),
                        polys=esg_provider.surface_polys,
                        points=esg_provider.surface_points,
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
        ],
    )
