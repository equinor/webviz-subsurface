import hashlib
from time import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import json

import numpy as np
from dash import Input, Output, State, callback, no_update

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._business_logic import EclipseGridDataModel
from ._layout import PROPERTYTYPE, LayoutElements


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
        Input(get_uuid(LayoutElements.GRID_COLUMNS), "value"),
        Input(get_uuid(LayoutElements.GRID_ROWS), "value"),
        Input(get_uuid(LayoutElements.GRID_LAYERS), "value"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
        State(get_uuid(LayoutElements.STORED_CELL_INDICES_HASH), "data"),
    )
    def _set_geometry_and_scalar(
        prop: List[str],
        date: List[int],
        columns: List[int],
        rows: List[int],
        layers: List[int],
        proptype: str,
        stored_cell_indices: int,
    ) -> Tuple[Any, Any, Any, List, Any]:

        timer = PerfTimer()
        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            scalar = datamodel.get_init_values(prop[0])
        else:
            scalar = datamodel.get_restart_values(prop[0], date[0])
        print(f"Reading scalar from file in {timer.lap_s():.2f}s")

        cropped_grid = datamodel.esg_provider.crop(columns, rows, layers)
        polys, points, cell_indices = datamodel.esg_provider.extract_skin(cropped_grid)
        print(f"Extracting cropped geometry in {timer.lap_s():.2f}s")

        # Storing hash of cell indices client side to control if only scalar should be updated
        hashed_indices = hashlib.sha256(cell_indices.data.tobytes()).hexdigest().upper()
        print(f"Hashing indices in {timer.lap_s():.2f}s")

        if hashed_indices == stored_cell_indices:
            return (
                no_update,
                no_update,
                scalar[cell_indices],
                [np.nanmin(scalar), np.nanmax(scalar)],
                no_update,
            )

        return (
            polys,
            points,
            scalar[cell_indices],
            [np.nanmin(scalar), np.nanmax(scalar)],
            hashed_indices,
        )

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
        Input(get_uuid(LayoutElements.Z_SCALE), "value"),
        State(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
    )
    def _set_representation_actor(z_scale: int, actor: Optional[dict]) -> dict:
        actor = actor if actor else {}
        actor.update({"scale": (1, 1, z_scale)})
        return actor

    @callback(
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "property"),
        Input(get_uuid(LayoutElements.SHOW_GRID_LINES), "value"),
        State(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "property"),
    )
    def _set_representation_property(
        show_grid_lines: int, properties: Optional[dict]
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
        Input(get_uuid(LayoutElements.VTK_VIEW), "clickInfo"),
        State(get_uuid(LayoutElements.Z_SCALE), "value"),
        State(get_uuid(LayoutElements.PROPERTIES), "value"),
        State(get_uuid(LayoutElements.DATES), "value"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
    )
    def _update_click_info(clickData, zscale, prop, date, proptype):

        if not clickData:
            return [""]
        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            scalar = datamodel.get_init_values(prop[0])
        else:
            scalar = datamodel.get_restart_values(prop[0], date[0])

        pos = clickData["worldPosition"]
        pos[2] = pos[2] / zscale

        timer = PerfTimer()

        cell_id, ijk = datamodel.esg_provider.find_containing_cell(pos)
        scalar_value = scalar[cell_id]

        propname = f"{prop[0]}-{date[0]}" if date else f"{prop[0]}"
        return json.dumps(
            {
                "x": pos[0],
                "y": pos[1],
                "z": pos[2],
                "i": ijk[0],
                "j": ijk[1],
                "k": ijk[2],
                propname: float(
                    scalar_value,
                ),
            },
            indent=2,
        )
