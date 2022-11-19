import warnings
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import xtgeo
from dash import Dash, Input, Output, State, callback_context, no_update
from dash._callback import NoUpdate
from dash.exceptions import PreventUpdate

from webviz_subsurface._datainput.well import (
    create_leaflet_well_marker_layer,
    make_well_layer,
)
from webviz_subsurface._models import SurfaceLeafletModel, SurfaceSetModel, WellSetModel


# pylint: disable=too-many-statements
def update_maps(
    app: Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
) -> None:
    @app.callback(
        Output({"id": get_uuid("map"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map1"), "layers"),
        Output({"id": get_uuid("map2"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map2"), "layers"),
        Output({"id": get_uuid("map3"), "element": "label"}, "children"),
        Output(get_uuid("leaflet-map3"), "layers"),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map1",
                "element": "surfaceattribute",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "surfaceattribute",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map1",
                "element": "surfacename",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "surfacename",
            },
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map1", "element": "ensemble"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map2", "element": "ensemble"},
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map1",
                "element": "calculation",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("map-settings"),
                "map_id": "map2",
                "element": "calculation",
            },
            "value",
        ),
        Input(get_uuid("leaflet-map1"), "switch"),
        Input(get_uuid("leaflet-map2"), "switch"),
        Input(get_uuid("leaflet-map3"), "switch"),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map1", "element": "options"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "map_id": "map2", "element": "options"},
            "value",
        ),
        Input(get_uuid("map-color-ranges"), "data"),
        Input(
            {"id": get_uuid("map-settings"), "settings": "compute_diff"},
            "value",
        ),
        Input(get_uuid("realization-store"), "data"),
        Input({"id": get_uuid("intersection-data"), "element": "well"}, "value"),
        Input({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
        Input({"id": get_uuid("map"), "element": "stored_xline"}, "data"),
        Input({"id": get_uuid("map"), "element": "stored_yline"}, "data"),
        Input({"id": get_uuid("intersection-data"), "element": "source"}, "value"),
        State(get_uuid("leaflet-map1"), "layers"),
        State(get_uuid("leaflet-map2"), "layers"),
        State(get_uuid("leaflet-map3"), "layers"),
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
            well = well_set_model.get_well(wellname)
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
            surface = surface_set_models[ensemble_map].calculate_statistical_surface(
                name=surfname_map,
                attribute=surfattr_map,
                calculation=calc_map,
                realizations=realizations,
            )
        else:
            surface = surface_set_models[ensemble_map].get_realization_surface(
                name=surfname_map, attribute=surfattr_map, realization=int(calc_map)
            )
        if calc_map2 in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
            surface2 = surface_set_models[ensemble_map2].calculate_statistical_surface(
                name=surfname_map2,
                attribute=surfattr_map2,
                calculation=calc_map2,
                realizations=realizations,
            )
        else:
            surface2 = surface_set_models[ensemble_map2].get_realization_surface(
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
        if well_set_model is not None:
            if options is not None or options2 is not None:
                if "intersect_well" in options or "intersect_well" in options2:
                    ### This is potentially a heavy task as it loads all wells into memory
                    wells: List[xtgeo.Well] = list(well_set_model.wells.values())
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

    @app.callback(
        Output({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
        Input(get_uuid("leaflet-map1"), "polyline_points"),
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

    @app.callback(
        Output(
            {"id": get_uuid("intersection-data"), "element": "source"},
            "value",
        ),
        Output(
            {"id": get_uuid("intersection-data"), "element": "well"},
            "value",
        ),
        Input(get_uuid("leaflet-map1"), "clicked_shape"),
        Input(get_uuid("leaflet-map1"), "polyline_points"),
    )
    def _update_from_map_click(
        clicked_shape: Optional[Dict],
        _polyline: List[List[float]],
    ) -> Tuple[str, Union[NoUpdate, str]]:
        """Update intersection source and optionally selected well when
        user clicks a shape in map"""
        ctx = callback_context.triggered[0]
        if "polyline_points" in ctx["prop_id"]:
            return "polyline", no_update
        if clicked_shape is None:
            raise PreventUpdate
        if clicked_shape.get("id") == "random_line":
            return "polyline", no_update
        if clicked_shape.get("id") in well_set_model.well_names:
            return "well", clicked_shape.get("id")
        raise PreventUpdate

    @app.callback(
        Output(get_uuid("map-color-ranges"), "data"),
        Output(
            {"id": get_uuid("map-settings"), "colors": "map2_clip_min"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("map-settings"), "colors": "map2_clip_max"},
            "disabled",
        ),
        Input(
            {"id": get_uuid("map-settings"), "colors": "map1_clip_min"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "colors": "map1_clip_max"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "colors": "map2_clip_min"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "colors": "map2_clip_max"},
            "value",
        ),
        Input(
            {"id": get_uuid("map-settings"), "colors": "sync_range"},
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
