import hashlib
import json
from time import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from dash import Input, Output, State, callback, no_update, callback_context, MATCH, ALL
from webviz_vtk.utils.vtk import b64_encode_numpy

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._eclipse_grid_datamodel import EclipseGridDataModel
from ._roff_grid_datamodel import RoffGridDataModel

from ._layout import PROPERTYTYPE, LayoutElements, GRID_DIRECTION


def plugin_callbacks(get_uuid: Callable, datamodel: EclipseGridDataModel) -> None:
    @callback(
        Output(get_uuid(LayoutElements.PROPERTIES), "options"),
        Output(get_uuid(LayoutElements.PROPERTIES), "value"),
        Output(get_uuid(LayoutElements.DATES), "options"),
        Output(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.INIT_RESTART), "value"),
    )
    def _populate_properties(
        init_restart: str,
    ) -> Tuple[
        List[Dict[str, str]], List[str], List[Dict[str, str]], Optional[List[str]]
    ]:
        if PROPERTYTYPE(init_restart) == PROPERTYTYPE.INIT:
            prop_names = datamodel.init_names
            dates = []
        else:
            prop_names = datamodel.restart_names
            dates = datamodel.restart_dates
        return (
            [{"label": prop, "value": prop} for prop in prop_names],
            [prop_names[0]],
            ([{"label": prop, "value": prop} for prop in dates]),
            [dates[0]] if dates else None,
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "polys"),
        Output(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "points"),
        Output(get_uuid(LayoutElements.VTK_GRID_CELLDATA), "values"),
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "colorDataRange"),
        Output(get_uuid(LayoutElements.STORED_CELL_INDICES_HASH), "data"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.GRID_RANGE_STORE), "data"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.STORED_CELL_INDICES_HASH), "data"),
    )
    def _set_geometry_and_scalar(
        prop: List[str],
        date: List[int],
        grid_range: List[List[int]],
        proptype: str,
        stored_cell_indices: int,
    ) -> Tuple[Any, Any, Any, List, Any]:

        timer = PerfTimer()
        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            scalar = datamodel.get_init_values(prop[0])
        else:
            scalar = datamodel.get_restart_values(prop[0], date[0])
        print(f"Reading scalar from file in {timer.lap_s():.2f}s")

        cropped_grid = datamodel.esg_accessor.crop(*grid_range)
        polys, points, cell_indices = datamodel.esg_accessor.extract_skin(cropped_grid)
        print(f"Extracting cropped geometry in {timer.lap_s():.2f}s")

        # Storing hash of cell indices client side to control if only scalar should be updated
        hashed_indices = hashlib.sha256(cell_indices.data.tobytes()).hexdigest().upper()
        print(f"Hashing indices in {timer.lap_s():.2f}s")

        if hashed_indices == stored_cell_indices:
            return (
                no_update,
                no_update,
                b64_encode_numpy(scalar[cell_indices].astype(np.float32)),
                [np.nanmin(scalar), np.nanmax(scalar)],
                no_update,
            )
        return (
            b64_encode_numpy(polys.astype(np.float32)),
            b64_encode_numpy(points.astype(np.float32)),
            b64_encode_numpy(scalar[cell_indices].astype(np.float32)),
            [np.nanmin(scalar), np.nanmax(scalar)],
            hashed_indices,
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "showCubeAxes"),
        Input(get_uuid(LayoutElements.Z_SCALE), "value"),
        Input(get_uuid(LayoutElements.SHOW_AXES), "value"),
        State(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
    )
    def _set_representation_actor(
        z_scale: int, axes_is_on: List[str], actor: Optional[dict]
    ) -> Tuple[dict, bool]:
        show_axes = bool(z_scale == 1 and axes_is_on)
        actor = actor if actor else {}
        actor.update({"scale": (1, 1, z_scale)})
        return actor, show_axes

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "property"),
        Input(get_uuid(LayoutElements.SHOW_GRID_LINES), "value"),
        State(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "property"),
    )
    def _set_representation_property(
        show_grid_lines: List[str], properties: Optional[dict]
    ) -> dict:
        properties = properties if properties else {}
        properties.update({"edgeVisibility": bool(show_grid_lines)})
        return properties

    @callback(
        Output(get_uuid(LayoutElements.VTK_VIEW), "triggerResetCamera"),
        Input(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "polys"),
        Input(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "points"),
        Input(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
    )
    def _reset_camera(_polys: np.ndarray, _points: np.ndarray, _actor: dict) -> float:
        return time()

    @callback(
        Output(get_uuid(LayoutElements.SELECTED_CELL), "children"),
        Output(get_uuid(LayoutElements.VTK_PICK_SPHERE), "state"),
        Output(get_uuid(LayoutElements.VTK_PICK_REPRESENTATION), "actor"),
        Input(get_uuid(LayoutElements.VTK_VIEW), "clickInfo"),
        Input(get_uuid(LayoutElements.ENABLE_PICKING), "value"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        Input(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.Z_SCALE), "value"),
        Input(get_uuid(LayoutElements.GRID_RANGE_STORE), "data"),
        State(get_uuid(LayoutElements.VTK_PICK_REPRESENTATION), "actor"),
    )
    # pylint: disable = too-many-locals, too-many-arguments
    def _update_click_info(
        click_data: Optional[Dict],
        enable_picking: Optional[str],
        prop: List[str],
        date: List[int],
        proptype: str,
        zscale: float,
        grid_range: List[List[int]],
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

        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            scalar = datamodel.get_init_values(prop[0])
        else:
            scalar = datamodel.get_restart_values(prop[0], date[0])

        cropped_grid = datamodel.esg_accessor.crop(*grid_range)

        # Getting position and ray below mouse position
        coords = click_data["worldPosition"].copy()

        ray = click_data["ray"]
        # Remove z-scaling from points
        coords[2] = coords[2] / zscale
        ray[0][2] = ray[0][2] / zscale
        ray[1][2] = ray[1][2] / zscale

        # Find the cell index and i,j,k of the closest cell the ray intersects
        cell_id, ijk = datamodel.esg_accessor.find_closest_cell_to_ray(
            cropped_grid, ray
        )

        # Get the scalar value of the cell index
        scalar_value = scalar[cell_id] if cell_id is not None else np.nan

        propname = f"{prop[0]}-{date[0]}" if date else f"{prop[0]}"
        return (
            json.dumps(
                {
                    "x": coords[0],
                    "y": coords[1],
                    "z": coords[2],
                    "i": ijk[0],
                    "j": ijk[1],
                    "k": ijk[2],
                    propname: float(
                        scalar_value,
                    ),
                },
                indent=2,
            ),
            {"center": click_data["worldPosition"], "radius": 100},
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
        return [[val, val + width] for val, width in zip(input_vals, width_vals)]
