import json
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xtgeo
from dash import ClientsideFunction, Dash, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

from webviz_subsurface._components import ColorPicker
from webviz_subsurface._models import SurfaceSetModel, WellSetModel

from ..figures.intersection import (
    get_plotly_trace_realization_surface,
    get_plotly_trace_statistical_surface,
    get_plotly_trace_well_trajectory,
    get_plotly_traces_uncertainty_envelope,
    get_plotly_zonelog_trace,
)


# pylint: disable=too-many-statements
def update_intersection(
    app: Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
    color_picker: ColorPicker,
    zonelog: Optional[str] = None,
) -> None:
    @app.callback(
        Output(get_uuid("intersection-graph-data"), "data"),
        Input(get_uuid("apply-intersection-data-selections"), "n_clicks"),
        Input(
            {"id": get_uuid("intersection-data"), "element": "source"},
            "value",
        ),
        Input({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
        Input({"id": get_uuid("map"), "element": "stored_xline"}, "data"),
        Input({"id": get_uuid("map"), "element": "stored_yline"}, "data"),
        Input({"id": get_uuid("intersection-data"), "element": "well"}, "value"),
        Input(get_uuid("realization-store"), "data"),
        State(
            {"id": get_uuid("intersection-data"), "element": "surface_attribute"},
            "value",
        ),
        State(
            {"id": get_uuid("intersection-data"), "element": "surface_names"}, "value"
        ),
        State(
            {"id": get_uuid("intersection-data"), "element": "calculation"},
            "value",
        ),
        State({"id": get_uuid("intersection-data"), "element": "ensembles"}, "value"),
        State({"id": get_uuid("intersection-data"), "element": "resolution"}, "value"),
        State({"id": get_uuid("intersection-data"), "element": "extension"}, "value"),
        State(color_picker.color_store_id, "data"),
    )
    # pylint: disable=too-many-arguments: disable=too-many-branches, too-many-locals
    def _store_intersection_traces(
        _apply_click: Optional[int],
        intersection_source: str,
        polyline: Optional[List],
        xline: Optional[List],
        yline: Optional[List],
        wellname: str,
        realizations: List[int],
        surfaceattribute: str,
        surfacenames: List[str],
        statistics: List[str],
        ensembles: str,
        resolution: float,
        extension: int,
        color_list: List[str],
    ) -> List:
        """Generate plotly traces for intersection figure and store clientside"""

        # TODO(Sigurd) Can we prohibit clearing of the sampling and extension input
        # fields (dcc.Input) in the client? Until we can, we must guard against sampling
        # and extension being None. This happens when the user clears the input field and we
        # have not yet found a solution that prohibits the input field from being cleared.
        # The situation can be slightly remedied by setting required=True which will highlight
        # the missing value with a red rectangle.
        if any(val is None for val in [resolution, extension]):
            raise PreventUpdate
        traces = []

        if intersection_source == "polyline":
            if polyline is None:
                return []
            fence_spec = get_fencespec_from_polyline(
                polyline, distance=resolution, atleast=5, nextend=extension / resolution
            )
        elif intersection_source == "xline":
            if xline is None:
                return []
            fence_spec = get_fencespec_from_polyline(
                xline, distance=resolution, atleast=5, nextend=extension / resolution
            )
        elif intersection_source == "yline":
            if yline is None:
                return []
            fence_spec = get_fencespec_from_polyline(
                yline, distance=resolution, atleast=5, nextend=extension / resolution
            )
        else:
            fence_spec = well_set_model.get_fence(
                well_name=wellname,
                distance=resolution,
                atleast=5,
                nextend=extension / resolution,
            )

        realizations = [int(real) for real in realizations]
        for ensemble in ensembles:
            surfset = surface_set_models[ensemble]
            for surfacename in surfacenames:
                color = color_picker.get_color(
                    color_list=color_list,
                    filter_query={
                        "surfacename": surfacename,
                        "ensemble": ensemble,
                    },
                )
                showlegend = True

                if statistics is not None:
                    for stat in ["Mean", "Min", "Max"]:
                        if stat in statistics:
                            trace = get_plotly_trace_statistical_surface(
                                surfaceset=surfset,
                                fence_spec=fence_spec,
                                calculation=stat,
                                legendname=f"{surfacename}({ensemble})",
                                name=surfacename,
                                attribute=surfaceattribute,
                                realizations=realizations,
                                showlegend=showlegend,
                                color=color,
                            )
                            traces.append(trace)
                            showlegend = False
                    if "Uncertainty envelope" in statistics:
                        envelope_traces = get_plotly_traces_uncertainty_envelope(
                            surfaceset=surfset,
                            fence_spec=fence_spec,
                            legendname=f"{surfacename}({ensemble})",
                            name=surfacename,
                            attribute=surfaceattribute,
                            realizations=realizations,
                            showlegend=showlegend,
                            color=color,
                        )
                        traces.extend(envelope_traces)
                        showlegend = False
                    if "Realizations" in statistics:
                        for real in realizations:
                            trace = get_plotly_trace_realization_surface(
                                surfaceset=surfset,
                                fence_spec=fence_spec,
                                legendname=f"{surfacename}({ensemble})",
                                name=surfacename,
                                attribute=surfaceattribute,
                                realization=real,
                                color=color,
                                showlegend=showlegend,
                            )
                            traces.append(trace)
                            showlegend = False
        if intersection_source == "well":
            well = well_set_model.get_well(wellname)
            traces.append(get_plotly_trace_well_trajectory(well))
            if well.zonelogname is not None:
                traces.extend(get_plotly_zonelog_trace(well, zonelog))

        return traces

    @app.callback(
        Output(get_uuid("intersection-graph-layout"), "data"),
        Input(get_uuid("intersection-graph-data"), "data"),
        Input(get_uuid("initial-intersection-graph-layout"), "data"),
        Input(
            {"id": get_uuid("intersection-data"), "element": "source"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "zrange_locks"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "zrange_min"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "zrange_max"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "ui_options"},
            "value",
        ),
        State(get_uuid("leaflet-map1"), "polyline_points"),
        State({"id": get_uuid("intersection-data"), "element": "well"}, "value"),
    )
    # pylint: disable=too-many-arguments, too-many-branches
    def _store_intersection_layout(
        data: List,
        initial_layout: Optional[dict],
        intersection_source: str,
        zrange_locks: str,
        zmin: Optional[float],
        zmax: Optional[float],
        ui_options: List[str],
        polyline: Optional[List],
        wellname: str,
    ) -> Dict:
        """Store intersection layout configuration clientside"""
        ctx = callback_context.triggered[0]
        if "ui_options" in ctx["prop_id"]:
            raise PreventUpdate

        # Set default layout
        layout: Dict = {
            "hovermode": "closest",
            "yaxis": {
                "autorange": "reversed",
                "showgrid": False,
                "zeroline": False,
                "title": "True vertical depth",
            },
            "xaxis": {
                "showgrid": False,
                "zeroline": False,
                "title": "Lateral resolution",
            },
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
        }

        # Update title to reflect source of cross-section calculation
        annotation_title = ["A", "A'"]
        if intersection_source in ["polyline", "xline", "yline"]:
            layout.update(
                {
                    "title": f"Intersection along {intersection_source} shown in Surface A"
                }
            )
            layout.get("xaxis", {}).update({"autorange": True})
            annotation_title = ["B", "B'"]
        if intersection_source == "well":
            layout["title"] = f"Intersection along well: {wellname}"

        # Set A-B annotations on plot
        layout["annotations"] = [
            {
                "x": 0,
                "y": 1,
                "xref": "paper",
                "yref": "paper",
                "text": f"<b>{annotation_title[0]}</b>",
                "font": {"size": 40},
                "showarrow": False,
            },
            {
                "x": 1,
                "y": 1,
                "xref": "paper",
                "yref": "paper",
                "text": f"<b>{annotation_title[1]}</b>",
                "font": {"size": 40},
                "showarrow": False,
            },
        ]
        # Update layout with any values provided from yaml configuration
        if initial_layout is not None:
            layout.update(initial_layout)

        # Return emptly plot layout if surface is source but no polyline is drawn
        if intersection_source == "polyline" and polyline is None:
            layout.update(
                {
                    "title": "Draw a random line from the toolbar on Surface A",
                }
            )
            return layout

        # Add any interactivily set range options
        if ui_options:
            if "uirevision" in ui_options:
                layout.update({"uirevision": "keep"})

        user_range = []
        if not (zmax is None and zmin is None):
            if "lock" in zrange_locks:
                if zmax is None:
                    zmax = max(
                        max(x for x in item["y"] if x is not None) for item in data
                    )
                if zmin is None:
                    zmin = min(
                        min(x for x in item["y"] if x is not None) for item in data
                    )
                user_range = [zmax, zmin]

            if "truncate" in zrange_locks:
                zmin_data = min(
                    min(x for x in item["y"] if x is not None) for item in data
                )
                zmax_data = max(
                    max(x for x in item["y"] if x is not None) for item in data
                )
                zmax = zmax if zmax is not None else zmax_data
                zmin = zmin if zmin is not None else zmin_data

                user_range = [min(zmax, zmax_data), max(zmin, zmin_data)]

        # Set y-axis range from depth range input if specified
        if user_range:
            layout.get("yaxis", {}).update({"autorange": False})
            layout.get("yaxis", {}).update(range=user_range)
        # Else autocalculate range if not intersecting a well
        elif intersection_source != "well":
            if "range" in layout.get("yaxis", {}):
                del layout["yaxis"]["range"]
            layout.get("yaxis", {}).update({"autorange": "reversed"})

        # Remove xaxis zero line
        layout.get("xaxis", {}).update({"zeroline": False, "showline": False})
        return layout

    # Store intersection data and layout to the plotly figure
    # Done clientside for performance
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="set_dcc_figure"),
        Output(get_uuid("intersection-graph"), "figure"),
        Input(get_uuid("intersection-graph-layout"), "data"),
        State(get_uuid("intersection-graph-data"), "data"),
    )

    @app.callback(
        Output(
            {"id": get_uuid("intersection-data"), "settings": "zrange_min"},
            "max",
        ),
        Output(
            {"id": get_uuid("intersection-data"), "settings": "zrange_max"},
            "min",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "zrange_min"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "settings": "zrange_max"},
            "value",
        ),
    )
    def _set_min_max_for_range_input(
        zmin: Optional[float],
        zmax: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        ctx = callback_context.triggered[0]
        if ctx["prop_id"] == ".":
            raise PreventUpdate

        return zmax, zmin

    @app.callback(
        Output(get_uuid("apply-intersection-data-selections"), "style"),
        Output(
            {
                "id": get_uuid("intersection-data"),
                "element": "stored_manual_update_options",
            },
            "data",
        ),
        Input(get_uuid("apply-intersection-data-selections"), "n_clicks"),
        Input(
            {"id": get_uuid("intersection-data"), "element": "surface_attribute"},
            "value",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "element": "surface_names"}, "value"
        ),
        Input(
            {"id": get_uuid("intersection-data"), "element": "calculation"},
            "value",
        ),
        Input({"id": get_uuid("intersection-data"), "element": "ensembles"}, "value"),
        Input({"id": get_uuid("intersection-data"), "element": "resolution"}, "value"),
        Input({"id": get_uuid("intersection-data"), "element": "extension"}, "value"),
        Input(color_picker.color_store_id, "data"),
        State(
            {
                "id": get_uuid("intersection-data"),
                "element": "stored_manual_update_options",
            },
            "data",
        ),
    )
    def _update_apply_button(
        _apply_click: Optional[int],
        surfaceattribute: str,
        surfacenames: List[str],
        statistics: List[str],
        ensembles: str,
        resolution: float,
        extension: int,
        color_list: List[str],
        previous_settings: Dict,
    ) -> Tuple[Dict, Dict]:

        ctx = callback_context.triggered[0]

        new_settings = {
            "surface_attribute": surfaceattribute,
            "surface_names": surfacenames,
            "calculation": statistics,
            "ensembles": ensembles,
            "resolution": resolution,
            "extension": extension,
            "colors": color_list,
        }
        # store selected settings if initial callback or apply button is pressed
        if (
            "apply-intersection-data-selections" in ctx["prop_id"]
            or ctx["prop_id"] == "."
        ):
            return {"background-color": "#E8E8E8"}, new_settings

        element = (
            "colors"
            if "colorpicker" in ctx["prop_id"]
            else json.loads(ctx["prop_id"].replace(".value", "")).get("element")
        )
        if new_settings[element] != previous_settings[element]:
            return {"background-color": "#7393B3", "color": "#fff"}, previous_settings
        return {"background-color": "#E8E8E8"}, previous_settings


def get_fencespec_from_polyline(
    coords: List, distance: float, atleast: int, nextend: Union[float, int]
) -> np.ndarray:
    """Create a fence specification from polyline coordinates"""
    poly = xtgeo.Polygons()
    poly.dataframe = pd.DataFrame(
        [
            {
                "X_UTME": c[0],
                "Y_UTMN": c[1],
                "Z_TVDSS": 0,
                "POLY_ID": 1,
                "NAME": "polyline",
            }
            for c in coords
        ]
    )
    return poly.get_fence(
        distance=distance, atleast=atleast, nextend=nextend, asnumpy=True
    )
