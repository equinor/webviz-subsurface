import datetime
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
import xtgeo
from dash import Input, Output, State, callback, callback_context
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._components import ColorPicker
from webviz_subsurface._models import SurfaceSetModel, WellSetModel

from .._figures.intersection import (
    get_plotly_trace_realization_surface,
    get_plotly_trace_statistical_surface,
    get_plotly_trace_well_trajectory,
    get_plotly_traces_uncertainty_envelope,
    get_plotly_zonelog_trace,
)
from .._plugin_ids import PluginIds
from .._view_elements import Graph


class StructView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        INTERSECTION = "intersection"
        SURFACE_A = "surface-a"
        SURFACE_B = "surface-b"
        SURFACE_A_B = "surface-a-b"

    def __init__(
        self,
        surface_set_models: Dict[str, SurfaceSetModel],
        well_set_model: WellSetModel,
        color_picker: ColorPicker,
        zonelog: Optional[str] = None,
    ) -> None:
        super().__init__("Intersect polyline from surface A")

        self.surface_set_models = surface_set_models
        self.well_set_model = well_set_model
        self.color_picker = color_picker
        self.zonelog = zonelog

        main_column = self.add_column()
        row_top = main_column.make_row()
        row_bottom = main_column.make_row()

        row_top.add_view_element(Graph("50vh"), StructView.Ids.INTERSECTION)
        row_bottom.add_view_element(Graph("25vh"), StructView.Ids.SURFACE_A)
        row_bottom.add_view_element(Graph("25vh"), StructView.Ids.SURFACE_B)
        row_bottom.add_view_element(Graph("25vh"), StructView.Ids.SURFACE_A_B)

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_DATA), "data"),
            #Input(get_uuid("apply-intersection-data-selections"), "n_clicks"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SOURCE),
                "value",
            ),
            Input({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.X_LINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.Y_LINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.WELL), "value"),
            Input(get_uuid("realization-store"), "data"),
            State(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTR),
                "value",
            ),
            State(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_NAMES), "value"
            ),
            State(
                self.get_store_unique_id(PluginIds.Stores.SHOW_SURFACES),
                "value",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "value"),
            State(self.get_store_unique_id(PluginIds.Stores.RESOLUTION), "value"),
            State(self.get_store_unique_id(PluginIds.Stores.EXTENSION), "value"),
            State(self.color_picker.color_store_id, "data"),
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
                fence_spec = self.well_set_model.get_fence(
                    well_name=wellname,
                    distance=resolution,
                    atleast=5,
                    nextend=extension / resolution,
                )

            realizations = [int(real) for real in realizations]
            for ensemble in ensembles:
                surfset = self.surface_set_models[ensemble]
                for surfacename in surfacenames:
                    color = self.color_picker.get_color(
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
                well = self.well_set_model.get_well(wellname)
                traces.append(get_plotly_trace_well_trajectory(well))
                if well.zonelogname is not None:
                    traces.extend(get_plotly_zonelog_trace(well, self.zonelog))

            return traces
        @callback(
            Output(get_uuid("intersection-graph-layout"), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_DATA), "data"),
            Input(get_uuid("initial-intersection-graph-layout"), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SOURCE),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.TRUNKATE_LOCK),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MIN),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MAX),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.KEEP_ZOOM),
                "value",
            ),
            State(get_uuid("leaflet-map1"), "polyline_points"),
            State(self.get_store_unique_id(PluginIds.Stores.WELL), "value"),
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
