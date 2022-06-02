from typing import List, Tuple

from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

import webviz_vtk
from dash import callback, Input, Output
from webviz_subsurface.plugins._grid_viewer._layout_elements import ElementIds
from ..settings import Settings


class VTKView3D(ViewElementABC):
    def __init__(self) -> None:
        super().__init__()
        self.add_settings_group(Settings(), ElementIds.Settings.ID)

    def inner_layout(self) -> Component:

        return webviz_vtk.View(
            id=self.register_component_unique_id(ElementIds.VTKVIEW3D.VIEW),
            style={"height": "90vh"},
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
                    id=self.register_component_unique_id(
                        ElementIds.VTKVIEW3D.GRID_REPRESENTATION
                    ),
                    showCubeAxes=True,
                    showScalarBar=True,
                    children=[
                        webviz_vtk.PolyData(
                            id=self.register_component_unique_id(
                                ElementIds.VTKVIEW3D.GRID_POLYDATA
                            ),
                            children=[
                                webviz_vtk.CellData(
                                    [
                                        webviz_vtk.DataArray(
                                            id=self.register_component_unique_id(
                                                ElementIds.VTKVIEW3D.GRID_CELLDATA
                                            ),
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
                    id=self.register_component_unique_id(
                        ElementIds.VTKVIEW3D.PICK_REPRESENTATION
                    ),
                    actor={"visibility": False},
                    children=[
                        webviz_vtk.Algorithm(
                            id=self.register_component_unique_id(
                                ElementIds.VTKVIEW3D.PICK_SPHERE
                            ),
                            vtkClass="vtkSphereSource",
                        )
                    ],
                ),
            ],
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    ElementIds.VTKVIEW3D.GRID_REPRESENTATION
                ).to_string(),
                "actor",
            ),
            Output(
                self.component_unique_id(
                    ElementIds.VTKVIEW3D.GRID_REPRESENTATION
                ).to_string(),
                "showCubeAxes",
            ),
            Input(
                self.settings_groups()[0]
                .component_unique_id(ElementIds.Settings.ZSCALE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_groups()[0]
                .component_unique_id(ElementIds.Settings.SHOW_CUBEAXES)
                .to_string(),
                "value",
            ),
        )
        def _set_representation_actor(
            z_scale: int, axes_is_on: List[str]
        ) -> Tuple[dict, bool]:
            show_axes = bool(z_scale == 1 and axes_is_on)
            actor = {"scale": (1, 1, z_scale)}
            return actor, show_axes
