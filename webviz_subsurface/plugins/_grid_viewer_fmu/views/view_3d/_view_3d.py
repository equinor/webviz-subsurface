from typing import Dict, List, Optional, Tuple

import numpy as np
from dash import Input, Output, State, callback, callback_context, html, no_update
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_vtk.utils.vtk import b64_encode_numpy

from webviz_subsurface._providers.ensemble_grid_provider import (
    CellFilter,
    EnsembleGridProvider,
    GridVizService,
    PropertySpec,
    Ray,
)

from ..._layout_elements import ElementIds
from ..._types import PROPERTYTYPE
from .settings import ColorScale, DataSettings, GridFilter, Settings
from .view_elements._vtk_view_3d_element import VTKView3D


class View3D(ViewABC):
    class Ids(StrEnum):
        VTKVIEW = "vtkview"
        DATASELECTORS = "data-selectors"
        GRIDFILTER = "grid-filter"
        SETTINGS = "settings"
        COLORSCALE = "color-scale"

    def __init__(
        self,
        grid_provider: EnsembleGridProvider,
        grid_viz_service: GridVizService,
        initial_grid_filter: Dict[str, int],
    ) -> None:
        super().__init__("Grid View")
        self.grid_provider = grid_provider
        self.grid_viz_service = grid_viz_service
        self.vtk_view_3d = VTKView3D()
        self.add_view_element(self.vtk_view_3d, View3D.Ids.VTKVIEW)
        self.add_settings_group(
            DataSettings(grid_provider=grid_provider), View3D.Ids.DATASELECTORS
        )
        self.add_settings_group(
            GridFilter(
                grid_provider=grid_provider, initial_grid_filter=initial_grid_filter
            ),
            View3D.Ids.GRIDFILTER,
        )
        self.add_settings_group(Settings(), View3D.Ids.SETTINGS)
        self.add_settings_group(ColorScale(), View3D.Ids.COLORSCALE)

    def _view_id(self, component_id: str) -> str:
        return (
            self.view_element(View3D.Ids.VTKVIEW)
            .component_unique_id(component_id)
            .to_string()
        )

    def _data_settings_id(self, component_id: str) -> str:
        return (
            self.settings_group(View3D.Ids.DATASELECTORS)
            .component_unique_id(component_id)
            .to_string()
        )

    def _visual_settings_id(self, component_id: str) -> str:
        return (
            self.settings_group(View3D.Ids.SETTINGS)
            .component_unique_id(component_id)
            .to_string()
        )

    def _color_scale_id(self, component_id: str) -> str:
        return (
            self.settings_group(View3D.Ids.COLORSCALE)
            .component_unique_id(component_id)
            .to_string()
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self._view_id(VTKView3D.Ids.GRID_POLYDATA),
                "polys",
            ),
            Output(
                self._view_id(VTKView3D.Ids.GRID_POLYDATA),
                "points",
            ),
            Output(
                self._view_id(VTKView3D.Ids.GRID_CELLDATA),
                "values",
            ),
            Output(
                self._view_id(VTKView3D.Ids.ACTUALVALUERANGE),
                "data",
            ),
            Output(self._view_id(VTKView3D.Ids.CAMERASET), "data"),
            Input(
                self._data_settings_id(DataSettings.Ids.PROPERTIES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.DATES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.REALIZATIONS),
                "value",
            ),
            Input(self.get_store_unique_id(ElementIds.IJK_CROP_STORE), "data"),
            State(
                self._data_settings_id(DataSettings.Ids.STATIC_DYNAMIC),
                "value",
            ),
            State(
                self._view_id(VTKView3D.Ids.GRID_POLYDATA),
                "polys",
            ),
            State(self._view_id(VTKView3D.Ids.CAMERASET), "data"),
        )
        def _set_geometry_and_scalar(
            prop: List[str],
            date: List[str],
            realizations: List[int],
            grid_range: List[List[int]],
            proptype: str,
            current_polys: str,
            camera_is_set: bool,
        ) -> Tuple:
            """Updates the geometry and scalar when realization, property or ijk filter
            is changed. Stores the scalar value range to a dcc.Store which is used to update
            the visualized scalar color range in a separate callback.
            On first execution updates a dcc.Store indicating that the camera must be reset,
            which is done in a separate callback.
            """

            if PROPERTYTYPE(proptype) == PROPERTYTYPE.STATIC:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=None)
            else:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

            triggered = callback_context.triggered[0]["prop_id"]

            if (
                triggered == "."
                or current_polys is None
                or self.get_store_unique_id(ElementIds.IJK_CROP_STORE) in triggered
                or self._data_settings_id(DataSettings.Ids.REALIZATIONS) in triggered
            ):
                surface_polys, scalars = self.grid_viz_service.get_surface(
                    provider_id=self.grid_provider.provider_id(),
                    realization=realizations[0],
                    property_spec=property_spec,
                    cell_filter=CellFilter(
                        i_min=grid_range[0][0],
                        i_max=grid_range[0][1],
                        j_min=grid_range[1][0],
                        j_max=grid_range[1][1],
                        k_min=grid_range[2][0],
                        k_max=grid_range[2][1],
                    ),
                )
                if scalars:
                    try:
                        value_range = [
                            np.nanmin(scalars.value_arr),
                            np.nanmax(scalars.value_arr),
                        ]
                    except (TypeError, ValueError):
                        value_range = [0, 1]
                else:
                    value_range = no_update
                return (
                    b64_encode_numpy(surface_polys.poly_arr),
                    b64_encode_numpy(surface_polys.point_arr.astype(np.float32)),
                    b64_encode_numpy(scalars.value_arr.astype(np.float32))
                    if scalars
                    else None,
                    value_range,
                    True if not camera_is_set else no_update,
                )

            scalars = self.grid_viz_service.get_mapped_property_values(
                provider_id=self.grid_provider.provider_id(),
                realization=realizations[0],
                property_spec=property_spec,
                cell_filter=CellFilter(
                    i_min=grid_range[0][0],
                    i_max=grid_range[0][1],
                    j_min=grid_range[1][0],
                    j_max=grid_range[1][1],
                    k_min=grid_range[2][0],
                    k_max=grid_range[2][1],
                ),
            )
            if scalars:
                try:
                    value_range = [
                        np.nanmin(scalars.value_arr),
                        np.nanmax(scalars.value_arr),
                    ]
                except (TypeError, ValueError):
                    value_range = [0, 1]
            else:
                value_range = no_update
            return (
                no_update,
                no_update,
                b64_encode_numpy(scalars.value_arr.astype(np.float32))
                if scalars
                else None,
                value_range,
                True if not camera_is_set else no_update,
            )

        @callback(
            Output(
                self._color_scale_id(ColorScale.Ids.COLORMIN),
                "disabled",
            ),
            Output(
                self._color_scale_id(ColorScale.Ids.COLORMAX),
                "disabled",
            ),
            Input(
                self._color_scale_id(ColorScale.Ids.COLORRANGEMANUAL),
                "value",
            ),
        )
        def _toggle_manual_color(enabled: List[str]) -> Tuple[bool, bool]:
            """Enables/disables the input fields to set manual color range
            of the scalar."""
            if enabled:
                return False, False
            return True, True

        @callback(
            Output(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "colorDataRange",
            ),
            Input(
                self._view_id(VTKView3D.Ids.ACTUALVALUERANGE),
                "data",
            ),
            Input(self._color_scale_id(ColorScale.Ids.COLORRANGEMANUAL), "value"),
            Input(self._color_scale_id(ColorScale.Ids.COLORMIN), "value"),
            Input(self._color_scale_id(ColorScale.Ids.COLORMAX), "value"),
        )
        def update_color_range(
            actual_value_range: List[float],
            should_use_manual: List[str],
            manual_min: Optional[float],
            manual_max: Optional[float],
        ) -> List[float]:
            """Sets the scalar color range, either from the data or from the manually
            set color range if active."""
            value_range = actual_value_range
            if should_use_manual:
                if manual_min:
                    value_range[0] = manual_min
                if manual_max:
                    value_range[1] = manual_max
            return value_range

        @callback(
            Output(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "actor",
            ),
            Output(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "showCubeAxes",
            ),
            Output(
                self._view_id(VTKView3D.Ids.VIEW),
                "triggerResetCamera",
            ),
            Input(
                self._visual_settings_id(Settings.Ids.ZSCALE),
                "value",
            ),
            Input(
                self._visual_settings_id(Settings.Ids.SHOW_CUBEAXES),
                "value",
            ),
            Input(self._view_id(VTKView3D.Ids.CAMERASET), "data"),
            Input(self._view_id(VTKView3D.Ids.RESETCAMERA), "n_clicks"),
            State(
                self._view_id(VTKView3D.Ids.VIEW),
                "triggerResetCamera",
            ),
        )
        def _set_representation_actor_and_camera(
            z_scale: int,
            axes_is_on: List[str],
            _camera_set: str,
            camcount: int,
            _btnclick: int,
        ) -> Tuple[Dict[str, Tuple[int, int, int]], bool, int]:
            """Handles updates to the geometry actor(z-scale), visible status
            of cubeaxis and triggers reset of camera position."""
            show_axes = bool(z_scale == 1 and axes_is_on)

            actor = {"scale": (1, 1, z_scale)}
            camcount = camcount if camcount else 0
            return actor, show_axes, camcount + 1

        @callback(
            Output(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "property",
            ),
            Input(
                self._visual_settings_id(Settings.Ids.SHOWGRIDLINES),
                "value",
            ),
            State(
                self._view_id(VTKView3D.Ids.VIEW),
                "property",
            ),
        )
        def update_geometry_property(
            gridlines_is_on: List[str],
            current_property: dict,
        ) -> dict:
            """Toggles visibility of gridlines"""
            prop = current_property if current_property else {}
            prop["edgeVisibility"] = bool(gridlines_is_on)
            return prop

        @callback(
            Output(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "colorMapPreset",
            ),
            Input(
                self._color_scale_id(ColorScale.Ids.COLORMAP),
                "value",
            ),
        )
        def _set_color_scale(colorscale: str) -> str:
            """Sets the scalar colorscale"""
            return colorscale

        @callback(
            Output(self._view_id(VTKView3D.Ids.CLICKED_DATA), "children"),
            Output(self._view_id(VTKView3D.Ids.PICK_SPHERE), "state"),
            Output(self._view_id(VTKView3D.Ids.PICK_REPRESENTATION), "actor"),
            Input(self._view_id(VTKView3D.Ids.VIEW), "clickInfo"),
            Input(
                self._data_settings_id(DataSettings.Ids.PROPERTIES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.DATES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.REALIZATIONS),
                "value",
            ),
            Input(self.get_store_unique_id(ElementIds.IJK_CROP_STORE), "data"),
            Input(
                self._data_settings_id(DataSettings.Ids.STATIC_DYNAMIC),
                "value",
            ),
            State(self._visual_settings_id(Settings.Ids.ZSCALE), "value"),
            State(self._view_id(VTKView3D.Ids.PICK_REPRESENTATION), "actor"),
        )

        # pylint: disable=too-many-locals
        def _update_click_info(
            click_data: Optional[Dict],
            prop: List[str],
            date: List[int],
            realizations: List[int],
            grid_range: List[List[int]],
            proptype: str,
            zscale: float,
            pick_representation_actor: Optional[Dict],
        ) -> Tuple:
            """Handles updates when a cell is clicked. Updates the readout panel, and
            position/visibility of the pick sphere geometry. IJK indices are converted
            from zero-based to one-based for the readout panel."""

            pick_representation_actor = (
                pick_representation_actor if pick_representation_actor else {}
            )
            if not click_data:
                return no_update, no_update, no_update

            pick_representation_actor.update({"visibility": True})

            client_world_pos = click_data["worldPosition"]
            client_ray = click_data["ray"]

            # Remove z-scaling from client ray
            client_world_pos[2] = client_world_pos[2] / zscale
            client_ray[0][2] = client_ray[0][2] / zscale
            client_ray[1][2] = client_ray[1][2] / zscale

            ray = Ray(origin=client_ray[0], end=client_ray[1])
            cell_filter = CellFilter(
                i_min=grid_range[0][0],
                i_max=grid_range[0][1],
                j_min=grid_range[1][0],
                j_max=grid_range[1][1],
                k_min=grid_range[2][0],
                k_max=grid_range[2][1],
            )

            if PROPERTYTYPE(proptype) == PROPERTYTYPE.STATIC:
                property_spec = PropertySpec(prop_name=prop[0], prop_date="")
            else:
                property_spec = PropertySpec(prop_name=prop[0], prop_date=str(date[0]))

            try:
                pick_result = self.grid_viz_service.ray_pick(
                    provider_id=self.grid_provider.provider_id(),
                    realization=realizations[0],
                    ray=ray,
                    property_spec=property_spec,
                    cell_filter=cell_filter,
                )
            except TypeError:
                return no_update, no_update, no_update
            if not pick_result:
                return no_update, no_update, no_update
            pick_sphere_pos = pick_result.intersection_point.copy()
            pick_sphere_pos[2] *= zscale

            propname = f"{prop[0]}-{date[0]}" if date else f"{prop[0]}"
            return (
                [
                    html.Div([html.B("Picked cell info")]),
                    html.Br(),
                    html.Div(
                        [
                            html.B("X: "),
                            f"{pick_result.intersection_point[0]:.2f}",
                        ]
                    ),
                    html.Div(
                        [
                            html.B("Y: "),
                            f"{pick_result.intersection_point[1]:.2f}",
                        ]
                    ),
                    html.Div(
                        [
                            html.B("Z: "),
                            f"{pick_result.intersection_point[2]:.2f}",
                        ]
                    ),
                    html.Div(
                        [
                            html.B("I: "),
                            pick_result.cell_i + 1,
                        ]
                    ),
                    html.Div(
                        [
                            html.B("J: "),
                            pick_result.cell_j + 1,
                        ]
                    ),
                    html.Div(
                        [
                            html.B("K: "),
                            pick_result.cell_k + 1,
                        ]
                    ),
                    html.Div(
                        [
                            html.B(f"{propname}: "),
                            f"{pick_result.cell_property_value:.2f}",
                        ]
                    ),
                ],
                {"center": pick_sphere_pos, "radius": 100},
                pick_representation_actor,
            )

        @callback(
            Output(self._view_id(VTKView3D.Ids.INFOBOX), "children"),
            Input(
                self._data_settings_id(DataSettings.Ids.PROPERTIES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.DATES),
                "value",
            ),
            Input(
                self._data_settings_id(DataSettings.Ids.REALIZATIONS),
                "value",
            ),
            Input(
                self._visual_settings_id(Settings.Ids.ZSCALE),
                "value",
            ),
            Input(
                self._view_id(VTKView3D.Ids.GRID_REPRESENTATION),
                "colorDataRange",
            ),
            Input(
                self._view_id(VTKView3D.Ids.ACTUALVALUERANGE),
                "data",
            ),
        )
        def update_infobox(
            properties: List[str],
            dates: List[str],
            realization: List[int],
            zscale: int,
            visual_value_range: List[float],
            actual_value_range: List[float],
        ) -> list:
            """Updates the information box with information on the visualized data."""
            return [
                html.Div([html.B("Property: "), html.Label(properties[0])]),
                html.Div(
                    [html.B("Date: "), html.Label(dates[0] if dates else "initial")]
                ),
                html.Div([html.B("Realization: "), html.Label(realization[0])]),
                html.Div([html.B("Z-Scale: "), html.Label(zscale)]),
                html.Div(
                    [
                        html.B("Visual value range: "),
                        html.Label(
                            f"{visual_value_range[0]:.2f} - {visual_value_range[1]:.2f}"
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.B("Actual value range: "),
                        html.Label(
                            f"{actual_value_range[0]:.2f} - {actual_value_range[1]:.2f}"
                        ),
                    ]
                ),
            ]

        @callback(
            Output(self._view_id(VTKView3D.Ids.INTERACTION_DIALOG), "open"),
            Input(self._view_id(VTKView3D.Ids.INTERACTION_DIALOG_BUTTON), "n_clicks"),
            State(self._view_id(VTKView3D.Ids.INTERACTION_DIALOG), "open"),
            prevent_initial_call=True,
        )
        def _open_interaction_dialog(_nclicks: int, is_open: bool) -> bool:
            """Open/close the dialog for mouse button settings"""
            return not is_open

        @callback(
            Output(self._view_id(VTKView3D.Ids.VIEW), "interactorSettings"),
            Output(self._view_id(VTKView3D.Ids.INTERACTION_DIALOG_READOUT), "children"),
            Input(self._view_id(VTKView3D.Ids.INTERACTION_CHECKLIST), "value"),
        )
        def _set_interaction_settings(modus: str) -> Tuple:
            """Updates the mouse button interaction bindings"""
            if modus == "resinsight_rms":
                return (
                    [
                        {
                            "button": 1,
                            "action": "Zoom",
                        },
                        {
                            "action": "ZoomToMouse",
                            "scrollEnabled": True,
                            "dragEnabled": False,
                        },
                        {
                            "button": 2,
                            "action": "Rotate",
                        },
                        {
                            "button": 3,
                            "action": "Pan",
                        },
                        {
                            "button": 1,
                            "action": "Pan",
                            "alt": True,
                        },
                        {
                            "button": 1,
                            "action": "Zoom",
                            "control": True,
                        },
                        {
                            "button": 1,
                            "action": "Select",
                            "shift": True,
                        },
                        {
                            "button": 1,
                            "action": "Roll",
                            "alt": True,
                            "shift": True,
                        },
                    ],
                    html.Div(
                        [
                            html.Div([html.B("Zoom: "), html.Label("Mouse1")]),
                            html.Div(
                                [html.B("ZoomToMouse: "), html.Label("Scroll")],
                            ),
                            html.Div([html.B("Rotate: "), html.Label("Mouse2")]),
                            html.Div([html.B("Pan: "), html.Label("Mouse3")]),
                            html.Div(
                                [html.B("Roll: "), html.Label("Alt+Shift+Mouse1")]
                            ),
                        ]
                    ),
                )

            return (
                [
                    {
                        "button": 1,
                        "action": "Rotate",
                    },
                    {
                        "button": 2,
                        "action": "Pan",
                    },
                    {
                        "button": 3,
                        "action": "Zoom",
                        "scrollEnabled": True,
                    },
                    {
                        "button": 1,
                        "action": "Pan",
                        "alt": True,
                    },
                    {
                        "button": 1,
                        "action": "Zoom",
                        "control": True,
                    },
                    {
                        "button": 1,
                        "action": "Select",
                        "shift": True,
                    },
                    {
                        "button": 1,
                        "action": "Roll",
                        "alt": True,
                        "shift": True,
                    },
                ],
                html.Div(
                    [
                        html.Div([html.B("Zoom: "), html.Label("Mouse3")]),
                        html.Div([html.B("Rotate: "), html.Label("Mouse1")]),
                        html.Div([html.B("Pan: "), html.Label("Mouse2")]),
                        html.Div([html.B("Roll: "), html.Label("Alt+Shift+Mouse1")]),
                    ]
                ),
            )
