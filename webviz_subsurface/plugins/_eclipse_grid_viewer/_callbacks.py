from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from dash import Input, Output, State, callback

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
        Output(get_uuid(LayoutElements.VTK_GRID_CELLDATA), "values"),
        Output(get_uuid(LayoutElements.VTK_GRID_REPRESENTATION), "colorDataRange"),
        Input(get_uuid(LayoutElements.PROPERTIES), "value"),
        Input(get_uuid(LayoutElements.DATES), "value"),
        State(get_uuid(LayoutElements.INIT_RESTART), "value"),
    )
    def _set_scalar(
        prop: List[str], date: List[int], proptype: str
    ) -> Tuple[np.array, list]:

        if PROPERTYTYPE(proptype) == PROPERTYTYPE.INIT:
            scalar = datamodel.get_init_property(prop[0])
        else:
            scalar = datamodel.get_restart_property(prop[0], date[0])

        polydata = datamodel.esg_provider.surface_polydata
        cell_indices = polydata["vtkOriginalCellIds"]
        polydata["scalar"] = scalar[cell_indices]
        return polydata["scalar"], [np.nanmin(scalar), np.nanmax(scalar)]
