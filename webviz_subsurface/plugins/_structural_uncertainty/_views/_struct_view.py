import warnings
from struct import Struct
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
import xtgeo
from dash import (
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    callback_context,
    clientside_callback,
    html,
    no_update,
)
from dash.dash import _NoUpdate
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._components import ColorPicker
from webviz_subsurface._datainput.well import (
    create_leaflet_well_marker_layer,
    make_well_layer,
)
from webviz_subsurface._models import SurfaceLeafletModel, SurfaceSetModel, WellSetModel

from .._figures.intersection import (
    get_plotly_trace_realization_surface,
    get_plotly_trace_statistical_surface,
    get_plotly_trace_well_trajectory,
    get_plotly_traces_uncertainty_envelope,
    get_plotly_zonelog_trace,
)
from .._plugin_ids import PluginIds
from .._shared_settings._intersection_controls import IntersectionControls
from .._view_elements import Graph


class StructView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        INTERSECTION = "intersection"
        SURFACE_A = "surface-a"
        SURFACE_B = "surface-b"
        SURFACE_A_B = "surface-a-b"
        MAP1 = "map1"
        LEAFLET_MAP1 = "leaflet-map1"
        MAP2 = "map2"
        LEAFLET_MAP2 = "leaflet-map2"
        MAP3 = "map3"
        LEAFLET_MAP3 = "leaflet-map3"
        ALL_MAPS = "all-maps"

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
        self.zonelog = zonelog
        self.color_picker = color_picker

    
        main_column = self.add_column()
        self.row_top = main_column.make_row()
        self.row_bottom = main_column.make_row()
        self.row_top.add_view_element(Graph("50vh"),StructView.Ids.INTERSECTION)
        self.row_bottom.make_column(StructView.Ids.MAP1)
        self.row_bottom.make_column(StructView.Ids.MAP2)
        self.row_bottom.make_column(StructView.Ids.MAP3)

       

    

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.COLOR_RANGES), "data"),
            Output(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MIN),
                "disabled",
            ),
            Output(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MAX),
                "disabled",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_A_MIN),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_A_MAX),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MIN),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MAX),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SYNC_RANGE_ON_MAPS),
                "value",
            ),
        )
        def _color_range_options(
            clip_min_map1: Optional[float],
            clip_max_map1: Optional[float],
            clip_min_map2: Optional[float],
            clip_max_map2: Optional[float],
            sync_range: list,
        ) -> Tuple[Dict[str, Dict], bool, bool]:
            ctx = callback_context.triggered[0]

            return (
                {
                    "map1": {
                        "color_range": [clip_min_map1, clip_max_map1],
                        "update": "map1" in ctx["prop_id"],
                    },
                    "map2": {
                        "color_range": [clip_min_map2, clip_max_map2]
                        if not sync_range
                        else [clip_min_map1, clip_max_map1],
                        "update": "map2" in ctx["prop_id"]
                        or (sync_range and "map1" in ctx["prop_id"])
                        or (
                            "sync_range" in ctx["prop_id"]
                            and [clip_min_map1, clip_max_map1]
                            != [clip_min_map2, clip_max_map2]
                        ),
                    },
                },
                bool(sync_range),
                bool(sync_range),
            )
        @callback(
            Output(
                self.layout_element(StructView.Ids.MAP1)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Output(
                self.layout_element(StructView.Ids.MAP2)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Output(
                self.layout_element(StructView.Ids.MAP3)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.FIRST_CALL),
                "data",
            )
        )
        def _create_maps(first: int) -> Tuple[Component]:
            print(first)
            
            return [
                    map_layout(
                                    uuid="map-layout-1",
                                    leaflet_id=StructView.Ids.LEAFLET_MAP1,
                                    synced_uuids=[
                                        StructView.Ids.LEAFLET_MAP2,
                                        StructView.Ids.LEAFLET_MAP3,
                                    ],
                                    draw_polyline=True,
                                ),
                    map_layout(
                                    uuid="map-layout-2",
                                    leaflet_id=StructView.Ids.LEAFLET_MAP2,
                                    synced_uuids=[
                                        StructView.Ids.LEAFLET_MAP1,
                                        StructView.Ids.LEAFLET_MAP3,
                                    ],
                                ),
                    map_layout(
                                    uuid="map-layout-3",
                                    leaflet_id=StructView.Ids.LEAFLET_MAP3,
                                    synced_uuids=[
                                        StructView.Ids.LEAFLET_MAP1,
                                        StructView.Ids.LEAFLET_MAP2,
                                    ],
                                ),
                ]
        @callback(
            Output({"id": "map-layout-1", "element": "label"}, "children"),
            Output(StructView.Ids.LEAFLET_MAP1, "layers"),
            Output({"id": "map-layout-2", "element": "label"}, "children"),
            Output(StructView.Ids.LEAFLET_MAP2, "layers"),
            Output({"id": "map-layout-3", "element": "label"}, "children"),
            Output(StructView.Ids.LEAFLET_MAP3, "layers"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTRIBUTE_A),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTRIBUTE_B),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_NAME_A),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_NAME_B),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLE_A),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLE_B),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.CALCULATION_REAL_A),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.CALCULATION_REAL_B),
                "data",
            ),
            Input(StructView.Ids.LEAFLET_MAP1, "switch"),
            Input(StructView.Ids.LEAFLET_MAP2, "switch"),
            Input(StructView.Ids.LEAFLET_MAP3, "switch"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.CALCULATE_WELL_INTER_A),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.CALCULATE_WELL_INTER_B),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.COLOR_RANGES), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.AUTO_COMP_DIFF),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.INITIAL_REALS), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.WELL), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.STORED_POLYLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_XLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_YLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SOURCE), "data"),
            State(StructView.Ids.LEAFLET_MAP1, "layers"),
            State(StructView.Ids.LEAFLET_MAP2, "layers"),
            State(StructView.Ids.LEAFLET_MAP3, "layers"),
            prevent_initial_call = True
        )
        # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
        def _update_maps(
            surfattr_map: str,
            surfattr_map2: str,
            surfname_map: str,
            surfname_map2: str,
            ensemble_map: str,
            ensemble_map2: str,
            calc_map: str,
            calc_map2: str,
            shade_map: Dict[str, bool],
            shade_map2: Dict[str, bool],
            shade_map3: Dict[str, bool],
            options: List[str],
            options2: List[str],
            color_range_settings: Dict,
            compute_diff: List[str],
            real_list: List[str],
            wellname: Optional[str],
            polyline: Optional[List],
            xline: Optional[List],
            yline: Optional[List],
            source: str,
            current_map: List,
            current_map2: List,
            current_map3: List,
        ) -> Tuple[str, List, str, List, str, List]:
            """Generate Leaflet layers for the three map views"""
            realizations = [int(real) for real in real_list]
            ctx = callback_context.triggered[0]
            if "compute_diff" in ctx["prop_id"]:
                if not compute_diff:
                    return (
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        [],
                    )

            # Check if map is already generated and should just be updated with polylines
            update_poly_only = bool(
                current_map
                and (
                    "stored_polyline" in ctx["prop_id"]
                    or "stored_yline" in ctx["prop_id"]
                    or "stored_xline" in ctx["prop_id"]
                )
            )
            if polyline is not None:
                poly_layer = create_leaflet_polyline_layer(
                    polyline, name="Polyline", poly_id="random_line"
                )
                for map_layers in [current_map, current_map2, current_map3]:
                    map_layers = replace_or_add_map_layer(
                        map_layers, "Polyline", poly_layer
                    )
            if xline is not None and source == "xline":
                xline_layer = create_leaflet_polyline_layer(
                    xline, name="Xline", poly_id="x_line"
                )
                for map_layers in [current_map, current_map2, current_map3]:
                    map_layers = replace_or_add_map_layer(map_layers, "Xline", xline_layer)
            if yline is not None and source == "yline":
                yline_layer = create_leaflet_polyline_layer(
                    yline, name="Yline", poly_id="y_line"
                )
                for map_layers in [current_map, current_map2, current_map3]:
                    map_layers = replace_or_add_map_layer(map_layers, "Yline", yline_layer)
            # If callback is triggered by polyline drawing, only update polyline
            if update_poly_only:
                return (
                    f"Surface A: {surfattr_map} - {surfname_map} - {ensemble_map} - {calc_map}",
                    current_map,
                    f"Surface B: {surfattr_map2} - {surfname_map2} - {ensemble_map2} - {calc_map2}",
                    no_update,
                    "Surface A-B",
                    no_update,
                )

            if wellname is not None:
                well = self.well_set_model.get_well(wellname)
                well_layer = make_well_layer(well, name=well.name)

                # If callback is triggered by well change, only update well layer
                if "well" in ctx["prop_id"] or (
                    "source" in ctx["prop_id"] and source == "well"
                ):
                    for map_layers in [current_map, current_map2, current_map3]:
                        map_layers = replace_or_add_map_layer(
                            map_layers, "Well", well_layer
                        )
                    return (
                        f"Surface A: {surfattr_map} - {surfname_map} - "
                        f"{ensemble_map} - {calc_map}",
                        current_map,
                        f"Surface B: {surfattr_map2} - {surfname_map2} - "
                        f"{ensemble_map2} - {calc_map2}",
                        current_map2,
                        "Surface A-B",
                        no_update,
                    )

            # Calculate maps
            if calc_map in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
                surface = self.surface_set_models[ensemble_map].calculate_statistical_surface(
                    name=surfname_map,
                    attribute=surfattr_map,
                    calculation=calc_map,
                    realizations=realizations,
                )
            else:
                surface = self.surface_set_models[ensemble_map].get_realization_surface(
                    name=surfname_map, attribute=surfattr_map, realization=int(calc_map)
                )
            if calc_map2 in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
                surface2 = self.surface_set_models[ensemble_map2].calculate_statistical_surface(
                    name=surfname_map2,
                    attribute=surfattr_map2,
                    calculation=calc_map2,
                    realizations=realizations,
                )
            else:
                surface2 = self.surface_set_models[ensemble_map2].get_realization_surface(
                    name=surfname_map2, attribute=surfattr_map2, realization=int(calc_map2)
                )

            # Generate Leaflet layers
            update_controls = check_if_update_needed(
                ctx=ctx,
                current_maps=[current_map, current_map2],
                compute_diff=compute_diff,
                color_range_settings=color_range_settings,
            )

            surface_layers = create_or_return_base_layer(
                update_controls,
                surface,
                current_map,
                shade_map,
                color_range_settings,
                map_id="map1",
            )
            surface_layers2 = create_or_return_base_layer(
                update_controls,
                surface2,
                current_map2,
                shade_map2,
                color_range_settings,
                map_id="map2",
            )

            try:
                surface3 = surface.copy()
                surface3.values = surface3.values - surface2.values

                diff_layers = (
                    [
                        SurfaceLeafletModel(
                            surface3,
                            name="surface3",
                            apply_shading=shade_map3.get("value", False),
                        ).layer
                    ]
                    if update_controls["diff_map"]["update"]
                    else []
                )
            except ValueError:
                diff_layers = []

            if wellname is not None:
                surface_layers.append(well_layer)
                surface_layers2.append(well_layer)
            if polyline is not None:
                surface_layers.append(poly_layer)
            if xline is not None and source == "xline":
                surface_layers.append(xline_layer)
            if yline is not None and source == "yline":
                surface_layers.append(yline_layer)
            if self.well_set_model is not None:
                if options is not None or options2 is not None:
                    if "intersect_well" in options or "intersect_well" in options2:
                        ### This is potentially a heavy task as it loads all wells into memory
                        wells: List[xtgeo.Well] = list(self.well_set_model.wells.values())
                    if "intersect_well" in options and update_controls["map1"]["update"]:
                        surface_layers.append(
                            create_leaflet_well_marker_layer(wells, surface)
                        )
                    if "intersect_well" in options2 and update_controls["map2"]["update"]:
                        surface_layers2.append(
                            create_leaflet_well_marker_layer(wells, surface2)
                        )

            return (
                f"Surface A: {surfattr_map} - {surfname_map} - {ensemble_map} - {calc_map}",
                surface_layers if update_controls["map1"]["update"] else no_update,
                f"Surface B: {surfattr_map2} - {surfname_map2} - {ensemble_map2} - {calc_map2}",
                surface_layers2 if update_controls["map2"]["update"] else no_update,
                "Surface A-B",
                diff_layers if update_controls["diff_map"]["update"] else no_update,
            )
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_DATA), "data"),
            Input(self.shared_settings_group(PluginIds.SharedSettings.INTERSECTION_CONTROLS)
                .component_unique_id(IntersectionControls.Ids.UPDATE_INTERSECTION)
                .to_string(), "n_clicks"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SOURCE),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.STORED_POLYLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_XLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_YLINE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.WELL), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.INITIAL_REALS), "data"),
            State(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTR),
                "data",
            ),
            State(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_NAMES), "data"
            ),
            State(
                self.get_store_unique_id(PluginIds.Stores.SHOW_SURFACES),
                "data",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
            State(self.get_store_unique_id(PluginIds.Stores.RESOLUTION), "data"),
            State(self.get_store_unique_id(PluginIds.Stores.EXTENSION), "data"),
            #State(self.color_picker.color_store_id, "data")
            prevent_initial_call = True
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
            ensembles: List[str],
            resolution: float,
            extension: int,
            #color_list: List[str],
        ) -> List:
            """Generate plotly traces for intersection figure and store clientside"""

            # TODO(Sigurd) Can we prohibit clearing of the sampling and extension input
            # fields (dcc.Input) in the client? Until we can, we must guard against sampling
            # and extension being None. This happens when the user clears the input field and we
            # have not yet found a solution that prohibits the input field from being cleared.
            # The situation can be slightly remedied by setting required=True which will highlight
            # the missing value with a red rectangle.
            print("click", _apply_click)
            color_list = self.color_picker._dframe['COLOR'].tolist()
           

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
            Output(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_LAYOUT), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_DATA), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.INIT_INTERSECTION_LAYOUT), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SOURCE),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.TRUNKATE_LOCK),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MIN),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MAX),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.KEEP_ZOOM),
                "data",
            ),
            State(StructView.Ids.LEAFLET_MAP1, "polyline_points"),
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

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.STORED_POLYLINE), "data"),
            Input(StructView.Ids.LEAFLET_MAP1, "polyline_points"),
        )
        def _store_polyline_points(
            positions_yx: List[List[float]],
        ) -> Optional[List[List[float]]]:
            """Stores drawn in polyline in a dcc.Store. Reversing elements to reflect
            normal behaviour"""
            if positions_yx is not None:
                try:
                    return [[pos[1], pos[0]] for pos in positions_yx]
                except TypeError:
                    warnings.warn("Polyline for map is not valid format")
                    return None
            raise PreventUpdate

        clientside_callback(
            ClientsideFunction(namespace="clientside", function_name="set_dcc_figure"),
            Output(self.view_element(StructView.Ids.INTERSECTION)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure"),
            Input(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_LAYOUT), "data"),
            State(self.get_store_unique_id(PluginIds.Stores.INTERSECTION_DATA), "data"),
        )

        # @callback(
        #     Output(
        #         self.get_store_unique_id(PluginIds.Stores.SOURCE),
        #         "data",
        #     ),
        #     Output(
        #         self.get_store_unique_id(PluginIds.Stores.WELL),
        #         "data",
        #     ),
        #     Input(StructView.Ids.LEAFLET_MAP1, "clicked_shape"),
        #     Input(StructView.Ids.LEAFLET_MAP1, "polyline_points"),
        #     prevent_initial_call = True
        # )
        # def _update_from_map_click(
        #     clicked_shape: Optional[Dict],
        #     _polyline: List[List[float]],
        # ) -> Tuple[str, Union[_NoUpdate, str]]:
        #     """Update intersection source and optionally selected well when
        #     user clicks a shape in map"""
        #     ctx = callback_context.triggered[0]
        #     if "polyline_points" in ctx["prop_id"]:
        #         return "polyline", no_update
        #     if clicked_shape is None:
        #         raise PreventUpdate
        #     if clicked_shape.get("id") == "random_line":
        #         return "polyline", no_update
        #     if clicked_shape.get("id") in self.well_set_model.well_names:
        #         return "well", clicked_shape.get("id")
        #     raise PreventUpdate





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


def map_layout(
    uuid: str,
    leaflet_id: str,
    synced_uuids: Optional[List[str]] = None,
    draw_polyline: bool = False,
) -> html.Div:
    synced_uuids = synced_uuids if synced_uuids else []
    props: Optional[Dict] = (
        {
            "drawTools": {
                "drawMarker": False,
                "drawPolygon": False,
                "drawPolyline": True,
                "position": "topright",
            }
        }
        if draw_polyline
        else {}
    )
    return html.Div(
        children=[
            html.Label(
                style={"textAlign": "center", "fontSize": "0.8em"},
                id={"id": uuid, "element": "label"},
            ),
            html.Div(
                style={
                    "height": "37vh",
                },
                children=LeafletMap(
                    syncedMaps=synced_uuids,
                    id=leaflet_id,
                    layers=[],
                    unitScale={},
                    autoScaleMap=True,
                    minZoom=-19,
                    updateMode="replace",
                    mouseCoords={"position": "bottomright"},
                    colorBar={"position": "bottomleft"},
                    switch={
                        "value": False,
                        "disabled": False,
                        "label": "Hillshading",
                    },
                    **props
                ),
            ),
        ],
    )


def create_leaflet_polyline_layer(
    positions: List[List[float]], name: str, poly_id: str
) -> Dict:
    return {
        "id": name,
        "name": name,
        "baseLayer": False,
        "checked": True,
        "action": "update",
        "data": [
            {
                "type": "polyline",
                "id": poly_id,
                "positions": positions,
                "color": "blue",
                "tooltip": "polyline",
            },
            {
                "type": "circle",
                "center": positions[0],
                "radius": 60,
                "color": "blue",
                "tooltip": "B",
            },
            {
                "type": "circle",
                "center": positions[-1],
                "radius": 60,
                "color": "blue",
                "tooltip": "B'",
            },
        ],
    }


def replace_or_add_map_layer(
    layers: List[Dict], uuid: str, new_layer: Dict
) -> List[Dict]:
    for idx, layer in enumerate(layers):
        if layer.get("id") == uuid:
            layers[idx] = new_layer
            return layers
    layers.append(new_layer)
    return layers


def check_if_update_needed(
    ctx: Dict,
    current_maps: List[List[Dict]],
    compute_diff: List,
    color_range_settings: Dict,
) -> Dict[str, Any]:

    update_controls = {}
    for map_id, current_map in zip(["map1", "map2"], current_maps):
        map_controllers_clicked = f'"map_id":"{map_id}"' in ctx["prop_id"]
        change_calculate_well_intersections = (
            map_controllers_clicked and "options" in ctx["prop_id"]
        )
        change_shade_map = (
            f"leaflet-{map_id}" in ctx["prop_id"] and "switch" in ctx["prop_id"]
        )
        change_color_clip = (
            "map-color-ranges" in ctx["prop_id"]
            and color_range_settings[map_id]["update"]
        )
        initial_loading = not current_map or all(
            layer.get("id") != map_id for layer in current_map
        )
        update_controls[map_id] = {
            "update": (
                map_controllers_clicked
                or change_shade_map
                or change_color_clip
                or initial_loading
            ),
            "use_base_layer": (change_shade_map or change_calculate_well_intersections),
        }

    change_diffmap_from_options = (
        "leaflet-map3" in ctx["prop_id"] and "switch" in ctx["prop_id"]
    ) or "compute_diff" in ctx["prop_id"]

    update_controls["diff_map"] = {
        "update": compute_diff
        and (
            (
                update_controls["map1"]["update"]
                and not update_controls["map1"]["use_base_layer"]
            )
            or (
                update_controls["map2"]["update"]
                and not update_controls["map2"]["use_base_layer"]
            )
            or change_diffmap_from_options
        )
        and not "map-color-ranges" in ctx["prop_id"]
    }

    return update_controls


def create_or_return_base_layer(
    update_controls: Dict,
    surface: xtgeo.RegularSurface,
    current_map: List[Dict],
    shade_map: Dict[str, bool],
    color_range_settings: Dict,
    map_id: str,
) -> List[Dict]:

    surface_layers = []
    if update_controls[map_id]["use_base_layer"]:
        for layer in current_map:
            if layer["baseLayer"]:
                layer["data"][0]["shader"]["applyHillshading"] = shade_map.get("value")
                surface_layers = [layer]
    else:
        surface_layers = [
            SurfaceLeafletModel(
                surface,
                clip_min=color_range_settings[map_id]["color_range"][0],
                clip_max=color_range_settings[map_id]["color_range"][1],
                name=map_id,
                apply_shading=shade_map.get("value", False),
            ).layer
        ]
    return surface_layers
