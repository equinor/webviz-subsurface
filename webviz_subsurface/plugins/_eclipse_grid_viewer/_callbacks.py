import hashlib
import json
from time import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from webviz_vtk.utils.vtk import b64_encode_numpy

from webviz_subsurface._utils.perf_timer import PerfTimer
from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProvider,
    GridVizService,
    PropertySpec,
    CellFilter,
    Ray,
)
from webviz_subsurface._providers.well_provider import WellProvider, WellServer

from ._layout import PROPERTYTYPE, LayoutElements, GRID_DIRECTION


def plugin_callbacks(
    get_uuid: Callable,
    grid_provider: EnsembleGridProvider,
    grid_viz_service: GridVizService,
    well_provider: WellProvider,
    well_server: WellServer,
) -> None:
    @callback(
        Output(get_uuid(LayoutElements.PROPERTIES), "options"),
        Output(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.INIT_RESTART), "value"),
    )
    def _populate_properties(
        init_restart: str,
    ) -> Tuple[
        List[Dict[str, str]], List[str], List[Dict[str, str]], Optional[List[str]]
    ]:
        if PROPERTYTYPE(init_restart) == PROPERTYTYPE.INIT:
            prop_names = grid_provider.static_property_names()

        else:
            prop_names = grid_provider.dynamic_property_names()

        return (
            [{"label": prop, "value": prop} for prop in prop_names],
            [prop_names[0]],
        )

    @callback(
        Output(get_uuid(LayoutElements.DATES), "options"),
        Output(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.DATES), "options"),
    )
    def _populate_dates(
        property_name: List[str],
        init_restart: str,
        current_date_options: List,
    ) -> Tuple[List[Dict[str, str]], Optional[List[str]]]:
        if PROPERTYTYPE(init_restart) == PROPERTYTYPE.INIT:
            return [], None
        else:
            property_name = property_name[0]
            dates = grid_provider.dates_for_dynamic_property(
                property_name=property_name
            )
            dates = dates if dates else []
            current_date_options = current_date_options if current_date_options else []
            if set(dates) == set(
                [dateopt["value"] for dateopt in current_date_options]
            ):
                return no_update, no_update
        return (
            ([{"label": prop, "value": prop} for prop in dates]),
            [dates[0]] if dates else None,
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "polys"),
        Output(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_GRID_CELLDATA), "values"),
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "colorDataRange"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.GRID_RANGE_STORE), "data"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "polys"),
    )
    def _set_geometry_and_scalar(
        prop: List[str],
        date: List[int],
        realizations: List[int],
        grid_range: List[List[int]],
        proptype: str,
        current_polys: str,
    ) -> Tuple[Any, Any, Any, List, Any]:

        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=0)
        else:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

        triggered = callback_context.triggered[0]["prop_id"]
        timer = PerfTimer()
        if (
            triggered == "."
            or current_polys is None
            or get_uuid(LayoutElements.GRID_RANGE_STORE) in triggered
            or get_uuid(LayoutElements.REALIZATIONS) in triggered
        ):
            surface_polys, scalars = grid_viz_service.get_surface(
                provider_id=grid_provider.provider_id(),
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

            return (
                b64_encode_numpy(surface_polys.poly_arr.astype(np.float32)),
                b64_encode_numpy(surface_polys.point_arr.astype(np.float32)),
                b64_encode_numpy(scalars.value_arr.astype(np.float32)),
                [np.nanmin(scalars.value_arr), np.nanmax(scalars.value_arr)],
            )
        else:
            scalars = grid_viz_service.get_mapped_property_values(
                provider_id=grid_provider.provider_id(),
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
            return (
                no_update,
                no_update,
                b64_encode_numpy(scalars.value_arr.astype(np.float32)),
                [np.nanmin(scalars.value_arr), np.nanmax(scalars.value_arr)],
            )

    @callback(
        Output(get_uuid(LayoutElements.VTK_WELL_INTERSECT_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_WELL_INTERSECT_POLYDATA), "polys"),
        Output(get_uuid(LayoutElements.VTK_WELL_INTERSECT_CELL_DATA), "values"),
        Output(get_uuid(LayoutElements.VTK_WELL_2D_INTERSECT_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_WELL_2D_INTERSECT_POLYDATA), "polys"),
        Output(get_uuid(LayoutElements.VTK_WELL_2D_INTERSECT_CELL_DATA), "values"),
        Output(get_uuid(LayoutElements.VTK_INTERSECT_VIEW), "cameraPosition"),
        Output(get_uuid(LayoutElements.VTK_INTERSECT_VIEW), "cameraFocalPoint"),
        Output(get_uuid(LayoutElements.VTK_INTERSECT_VIEW), "cameraViewUp"),
        Output(get_uuid(LayoutElements.VTK_INTERSECT_VIEW), "cameraParallelHorScale"),
        Output(get_uuid(LayoutElements.LINEGRAPH), "figure"),
        Input(get_uuid(LayoutElements.WELL_SELECT), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
    )
    def set_well_geometries(
        well_names: List[str],
        realizations: List[int],
        prop: List[str],
        date: List[int],
        proptype: str,
    ) -> Tuple[
        List[Dict[str, str]], List[str], List[Dict[str, str]], Optional[List[str]]
    ]:

        if not well_names:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )
        polyline_xy = np.array(
            well_provider.get_polyline_along_well_path_SIMPLIFIED(well_names[0])
        )
        polyline_xy_full = np.array(
            well_provider.get_polyline_along_well_path_SIMPLIFIED(
                well_names[0], use_rdp=False
            )
        )

        print(polyline_xy[:, 0], polyline_xy[:, 1])
        print(polyline_xy_full)

        def plotly_xy_plot(xy, xy2):
            return {
                "data": [
                    {
                        "x": xy[:, 0],
                        "y": xy[:, 1],
                        "marker": dict(
                            size=20,
                            line=dict(color="MediumPurple", width=8),
                        ),
                    },
                    {"x": xy2[:, 0], "y": xy2[:, 1]},
                ]
            }

        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=0)
        else:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

        surface_polys, scalars = grid_viz_service.cut_along_polyline(
            provider_id=grid_provider.provider_id(),
            realization=realizations[0],
            polyline_xy=np.array(polyline_xy).flatten(),
            property_spec=property_spec,
        )

        approx_plane_normal = _calc_approx_plane_normal_from_polyline_xy(polyline_xy)

        surf_points_3d = np.asarray(surface_polys.point_arr).reshape(-1, 3)
        bb_min = np.min(surf_points_3d, axis=0)
        bb_max = np.max(surf_points_3d, axis=0)
        bb_radius = np.linalg.norm(bb_max - bb_min) / 2

        center_pt = (bb_max + bb_min) / 2.0
        eye_pt = center_pt + bb_radius * approx_plane_normal
        view_up_vec = [0.0, 0.0, 1.0]

        # Make scale slightly larger so we get some space on each side of the viewport
        cameraParallelHorScale = bb_radius * 1.05

        return (
            b64_encode_numpy(surface_polys.point_arr),
            b64_encode_numpy(surface_polys.poly_arr),
            b64_encode_numpy(scalars.value_arr) if scalars is not None else no_update,
            b64_encode_numpy(surface_polys.point_arr),
            b64_encode_numpy(surface_polys.poly_arr),
            b64_encode_numpy(scalars.value_arr) if scalars is not None else no_update,
            eye_pt,
            center_pt,
            view_up_vec,
            cameraParallelHorScale,
            plotly_xy_plot(polyline_xy, polyline_xy_full),
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_WELL_PATH_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_WELL_PATH_POLYDATA), "lines"),
        Output(get_uuid(LayoutElements.VTK_WELL_PATH_2D_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_WELL_PATH_2D_POLYDATA), "lines"),
        Input(get_uuid(LayoutElements.WELL_SELECT), "value"),
    )
    def set_well_geometries(
        well_names: List[str],
    ) -> Tuple[
        List[Dict[str, str]], List[str], List[Dict[str, str]], Optional[List[str]]
    ]:

        if not well_names:
            return no_update, no_update, no_update, no_update, no_update
        polyline = well_server.get_polyline(
            provider_id=well_provider.provider_id(), well_name=well_names[0]
        )

        return (
            b64_encode_numpy(polyline.point_arr.astype(np.float32)),
            b64_encode_numpy(polyline.line_arr.astype(np.float32)),
            b64_encode_numpy(polyline.point_arr.astype(np.float32)),
            b64_encode_numpy(polyline.line_arr.astype(np.float32)),
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
        Output(get_uuid(LayoutElements.VTK_WELL_INTERSECT_REPRESENTATION), "actor"),
        Output(get_uuid(LayoutElements.VTK_WELL_PATH_REPRESENTATION), "actor"),
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "showCubeAxes"),
        Input(get_uuid(LayoutElements.Z_SCALE), "value"),
        Input(get_uuid(LayoutElements.SHOW_AXES), "value"),
    )
    def _set_representation_actor(
        z_scale: int, axes_is_on: List[str]
    ) -> Tuple[dict, bool]:
        show_axes = bool(z_scale == 1 and axes_is_on)
        actor = {"scale": (1, 1, z_scale)}
        return actor, actor, actor, show_axes

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "property"),
        Output(get_uuid(LayoutElements.VTK_WELL_INTERSECT_REPRESENTATION), "property"),
        Input(get_uuid(LayoutElements.SHOW_GRID_LINES), "value"),
    )
    def _set_representation_property(
        show_grid_lines: List[str],
    ) -> dict:
        properties = {"edgeVisibility": bool(show_grid_lines)}

        return properties, properties

    @callback(
        Output(get_uuid(LayoutElements.VTK_VIEW), "triggerResetCamera"),
        Input(get_uuid(LayoutElements.REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
    )
    def _reset_camera(realizations: List[int], _actor: dict) -> float:

        return time()

    @callback(
        Output(get_uuid(LayoutElements.SELECTED_CELL), "children"),
        Output(get_uuid(LayoutElements.VTK_PICK_SPHERE), "state"),
        Output(get_uuid(LayoutElements.VTK_PICK_REPRESENTATION), "actor"),
        Input(get_uuid(LayoutElements.VTK_VIEW), "clickInfo"),
        Input(get_uuid(LayoutElements.ENABLE_PICKING), "value"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONS), "value"),
        Input(get_uuid(LayoutElements.GRID_RANGE_STORE), "data"),
        Input(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.Z_SCALE), "value"),
        State(get_uuid(LayoutElements.VTK_PICK_REPRESENTATION), "actor"),
    )
    # pylint: disable = too-many-locals, too-many-arguments
    def _update_click_info(
        click_data: Optional[Dict],
        enable_picking: Optional[str],
        prop: List[str],
        date: List[int],
        realizations: List[int],
        grid_range: List[List[int]],
        proptype: str,
        zscale: float,
        pick_representation_actor: Optional[Dict],
    ) -> Tuple[str, Dict[str, Any], Dict[str, bool]]:
        pick_representation_actor = (
            pick_representation_actor if pick_representation_actor else {}
        )
        if not click_data:
            return no_update, no_update, no_update
        if not enable_picking:
            pick_representation_actor.update({"visibility": False})
            return "", {}, pick_representation_actor
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

        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=0)
        else:
            property_spec = PropertySpec(prop_name=prop[0], prop_date=date[0])

        pick_result = grid_viz_service.ray_pick(
            provider_id=grid_provider.provider_id(),
            realization=realizations[0],
            ray=ray,
            property_spec=property_spec,
            cell_filter=cell_filter,
        )

        pick_sphere_pos = pick_result.intersection_point.copy()
        pick_sphere_pos[2] *= zscale

        propname = f"{prop[0]}-{date[0]}" if date else f"{prop[0]}"
        return (
            json.dumps(
                {
                    "x": pick_result.intersection_point[0],
                    "y": pick_result.intersection_point[1],
                    "z": pick_result.intersection_point[2],
                    "i": pick_result.cell_i,
                    "j": pick_result.cell_j,
                    "k": pick_result.cell_k,
                    propname: float(pick_result.cell_property_value),
                },
                indent=2,
            ),
            {"center": pick_sphere_pos, "radius": 100},
            pick_representation_actor,
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "colorMapPreset"),
        Input(get_uuid(LayoutElements.COLORMAP), "value"),
    )
    def _set_colormap(colormap: str) -> str:
        return colormap

    @callback(
        Output(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": MATCH,
                "component": "input",
                "component2": MATCH,
            },
            "value",
        ),
        Output(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": MATCH,
                "component": "slider",
                "component2": MATCH,
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": MATCH,
                "component": "input",
                "component2": MATCH,
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": MATCH,
                "component": "slider",
                "component2": MATCH,
            },
            "value",
        ),
    )
    def _synchronize_crop_slider_and_input(
        input_val: int, slider_val: int
    ) -> Tuple[Any, Any]:
        trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        if "slider" in trigger_id:
            return slider_val, no_update
        return no_update, input_val

    @callback(
        Output(get_uuid(LayoutElements.GRID_RANGE_STORE), "data"),
        Input(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": ALL,
                "component": "input",
                "component2": "start",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid(LayoutElements.CROP_WIDGET),
                "direction": ALL,
                "component": "input",
                "component2": "width",
            },
            "value",
        ),
    )
    def _store_grid_range_from_crop_widget(
        input_vals: List[int], width_vals: List[int]
    ) -> List[List[int]]:
        if not input_vals or not width_vals:
            return no_update
        return [[val, val + width - 1] for val, width in zip(input_vals, width_vals)]


def _calc_approx_plane_normal_from_polyline_xy(polyline_xy: List[float]) -> List[float]:
    polyline_np = np.asarray(polyline_xy).reshape(-1, 2)
    num_points_in_polyline = len(polyline_np)

    aggr_right_vec = np.array([0.0, 0.0])
    for i in range(0, num_points_in_polyline - 1):
        p0 = polyline_np[i]
        p1 = polyline_np[i + 1]
        fwd_vec = p1 - p0
        fwd_vec /= np.linalg.norm(fwd_vec)
        right_vec = np.array([fwd_vec[1], -fwd_vec[0]])
        aggr_right_vec += right_vec

    avg_right_vec = aggr_right_vec / np.linalg.norm(aggr_right_vec)
    approx_plane_normal = np.array([aggr_right_vec[0], aggr_right_vec[1], 0])

    return approx_plane_normal
