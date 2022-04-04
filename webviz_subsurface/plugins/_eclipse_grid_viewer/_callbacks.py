import hashlib
from time import time
from typing import Any, Callable, Dict, List, Optional, Tuple

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
            scalar = datamodel.get_init_property(prop[0])
        else:
            scalar = datamodel.get_restart_property(prop[0], date[0])
        print(f"Reading scalar from file in {timer.lap_s():.2f}s")

        polys, points, cell_indices = datamodel.esg_provider.crop(columns, rows, layers)
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
    def _set_actor(z_scale: int, actor: Optional[dict]) -> dict:
        actor = actor if actor else {}
        actor.update({"scale": (1, 1, z_scale)})
        return actor

    @callback(
        Output(get_uuid(LayoutElements.VTK_VIEW), "triggerResetCamera"),
        Input(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "polys"),
        Input(get_uuid(LayoutElements.VTK_GRID_POLYDATA), "points"),
        Input(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "actor"),
    )
    def _reset_camera(_polys: np.ndarray, _points: np.ndarray, _actor: dict) -> float:
        return time()
