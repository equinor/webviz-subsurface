import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    EnsembleSurfaceProvider,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)

import xtgeo
from dash import Dash, Input, Output, State, callback_context, no_update
from dash.dash import _NoUpdate
from dash.exceptions import PreventUpdate

from webviz_subsurface._datainput.well import (
    create_leaflet_well_marker_layer,
    make_well_layer,
)
from webviz_subsurface._models import SurfaceLeafletModel, SurfaceSetModel, WellSetModel
from webviz_subsurface._providers import (
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    QualifiedSurfaceAddress,
    QualifiedDiffSurfaceAddress,
    WellProvider,
    WellServer,
)

from webviz_subsurface._components.deckgl_map.deckgl_map_layers_model import (
    DeckGLMapLayersModel,
)
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    GeoJsonLayer,
    WellsLayer,
)

# pylint: disable=too-many-statements
def update_maps(
    app: Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
    surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: SurfaceServer,
    well_provider: WellProvider,
    well_server: WellServer,
) -> None:
    @app.callback(
        Output(get_uuid("deckgl"), "layers"),
        Output(get_uuid("deckgl"), "bounds"),
        Output(get_uuid("deckgl"), "views"),
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
        State(get_uuid("deckgl"), "layers"),
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
        current_layers: List,
    ) -> Tuple[str, List, str, List, str, List]:
        """Generate Leaflet layers for the three map views"""
        realizations = [int(real) for real in real_list]
        ctx = callback_context.triggered[0]
        if "compute_diff" in ctx["prop_id"]:
            if not compute_diff:
                return no_update

        # if polyline is not None:
        #     poly_layer = create_leaflet_polyline_layer(
        #         polyline, name="Polyline", poly_id="random_line"
        #     )
        #     for map_layers in [current_map, current_map2, current_map3]:
        #         map_layers = replace_or_add_map_layer(
        #             map_layers, "Polyline", poly_layer
        #         )
        # if xline is not None and source == "xline":
        #     xline_layer = create_leaflet_polyline_layer(
        #         xline, name="Xline", poly_id="x_line"
        #     )
        #     for map_layers in [current_map, current_map2, current_map3]:
        #         map_layers = replace_or_add_map_layer(map_layers, "Xline", xline_layer)
        # if yline is not None and source == "yline":
        #     yline_layer = create_leaflet_polyline_layer(
        #         yline, name="Yline", poly_id="y_line"
        #     )
        #     for map_layers in [current_map, current_map2, current_map3]:
        #         map_layers = replace_or_add_map_layer(map_layers, "Yline", yline_layer)
        # # If callback is triggered by polyline drawing, only update polyline

        # if wellname is not None:
        #     well = well_set_model.get_well(wellname)
        #     well_layer = make_well_layer(well, name=well.name)

        #     # If callback is triggered by well change, only update well layer
        #     if "well" in ctx["prop_id"] or (
        #         "source" in ctx["prop_id"] and source == "well"
        #     ):
        #         for map_layers in [current_map, current_map2, current_map3]:
        #             map_layers = replace_or_add_map_layer(
        #                 map_layers, "Well", well_layer
        #             )

        # Calculate maps
        if calc_map in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
            surface_address = StatisticalSurfaceAddress(
                name=surfname_map,
                attribute=surfattr_map,
                realizations=realizations,
                datestr=None,
                statistic=calc_map,
            )

        else:
            surface_address = SimulatedSurfaceAddress(
                name=surfname_map,
                attribute=surfattr_map,
                realization=int(calc_map),
                datestr=None,
            )

        if calc_map2 in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]:
            surface_address2 = StatisticalSurfaceAddress(
                name=surfname_map2,
                attribute=surfattr_map2,
                realizations=realizations,
                datestr=None,
                statistic=calc_map2,
            )

        else:
            surface_address2 = SimulatedSurfaceAddress(
                name=surfname_map2,
                attribute=surfattr_map2,
                realization=int(calc_map2),
                datestr=None,
            )
        qualified_address = QualifiedSurfaceAddress(
            provider_id=surface_providers[ensemble_map].provider_id(),
            address=surface_address,
        )
        qualified_address2 = QualifiedSurfaceAddress(
            provider_id=surface_providers[ensemble_map2].provider_id(),
            address=surface_address2,
        )

        surf_spec, viewport_bounds = get_surface_specification(
            provider=surface_providers[ensemble_map],
            qualified_address=qualified_address,
            surface_server=surface_server,
        )
        surf_spec2, _ = get_surface_specification(
            provider=surface_providers[ensemble_map2],
            qualified_address=qualified_address2,
            surface_server=surface_server,
        )

        surface2 = surface_providers[ensemble_map2].get_surface(surface_address2)
        qualified_diff_address = QualifiedDiffSurfaceAddress(
            provider_id_a=qualified_address.provider_id,
            address_a=qualified_address.address,
            provider_id_b=qualified_address2.provider_id,
            address_b=qualified_address2.address,
        )

        diff_surf_spec, _ = get_diff_surface_specification(
            provider_a=surface_providers[ensemble_map],
            provider_b=surface_providers[ensemble_map2],
            qualified_address=qualified_diff_address,
            surface_server=surface_server,
        )
        layer_model = DeckGLMapLayersModel(layers=current_layers)

        layer_model.update_layer_by_id(
            layer_id="colormap",
            layer_data=surf_spec,
        )

        layer_model.update_layer_by_id(
            layer_id="hillshading",
            layer_data=surf_spec,
        )
        layer_model.update_layer_by_id(
            layer_id="colormap",
            layer_data={
                "colorMapName": "Physics",
                "colorMapRange": surf_spec["valueRange"],
            },
        )
        layer_model.update_layer_by_id(
            layer_id="colormap2",
            layer_data=surf_spec2,
        )

        layer_model.update_layer_by_id(
            layer_id="hillshading2",
            layer_data=surf_spec2,
        )
        layer_model.update_layer_by_id(
            layer_id="colormap2",
            layer_data={
                "colorMapName": "Physics",
                "colorMapRange": surf_spec2["valueRange"],
            },
        )
        layer_model.update_layer_by_id(
            layer_id="colormap3",
            layer_data=diff_surf_spec,
        )

        layer_model.update_layer_by_id(
            layer_id="colormap3",
            layer_data={
                "colorMapName": "Physics",
                "colorMapRange": diff_surf_spec["valueRange"],
            },
        )

        if wellname is not None:
            well = well_provider.get_well_xtgeo_obj(wellname)
        #     surface_layers.append(well_layer)
        #     surface_layers2.append(well_layer)
        if polyline is not None:
            layer_model.update_layer_by_id(
                layer_id="polyline",
                layer_data={"data": make_geojson_polyline(polyline)},
            )
        if xline is not None:  # and source == "xline":
            layer_model.update_layer_by_id(
                layer_id="x_line", layer_data={"data": make_geojson_polyline(xline)}
            )
        if polyline is not None:
            layer_model.update_layer_by_id(
                layer_id="polline", layer_data={"data": make_geojson_polyline(polyline)}
            )
        if yline is not None:  # and source == "yline":
            layer_model.update_layer_by_id(
                layer_id="y_line", layer_data={"data": make_geojson_polyline(yline)}
            )

        #     surface_layers.append(poly_layer)
        # if xline is not None and source == "xline":
        #     surface_layers.append(xline_layer)
        # if yline is not None and source == "yline":
        #     surface_layers.append(yline_layer)
        # if well_set_model is not None:
        #     if options is not None or options2 is not None:
        #         if "intersect_well" in options or "intersect_well" in options2:
        #             ### This is potentially a heavy task as it loads all wells into memory
        #             wells: List[xtgeo.Well] = list(well_set_model.wells.values())
        #         if "intersect_well" in options and update_controls["map1"]["update"]:
        #             surface_layers.append(
        #                 create_leaflet_well_marker_layer(wells, surface)
        #             )
        #         if "intersect_well" in options2 and update_controls["map2"]["update"]:
        #             surface_layers2.append(
        #                 create_leaflet_well_marker_layer(wells, surface2)
        #             )

        return (
            layer_model.layers,
            viewport_bounds,
            {
                "layout": [1, 3],
                "showLabel": True,
                "viewports": [
                    {
                        "id": "1_view",
                        "show3D": False,
                        "layerIds": [
                            "colormap",
                            "hillshading",
                            "drawinglayer",
                            "x_line",
                            "y_line",
                        ],
                        "name": f"{surfattr_map} - {surfname_map} - {ensemble_map} - {calc_map}",
                    },
                    {
                        "id": "2_view",
                        "show3D": False,
                        "layerIds": ["colormap2", "hillshading2", "x_line", "y_line"],
                        "name": f"{surfattr_map2} - {surfname_map2} - {ensemble_map2} - {calc_map2}",
                    },
                    {
                        "id": "3_view",
                        "show3D": False,
                        "layerIds": ["colormap3", "x_line", "y_line"],
                        "name": "Difference between A and B",
                    },
                ],
            },
        )

    # @app.callback(
    #     Output({"id": get_uuid("map"), "element": "stored_polyline"}, "data"),
    #     Input(get_uuid("leaflet-map1"), "polyline_points"),
    # )
    # def _store_polyline_points(
    #     positions_yx: List[List[float]],
    # ) -> Optional[List[List[float]]]:
    #     """Stores drawn in polyline in a dcc.Store. Reversing elements to reflect
    #     normal behaviour"""
    #     if positions_yx is not None:
    #         try:
    #             return [[pos[1], pos[0]] for pos in positions_yx]
    #         except TypeError:
    #             warnings.warn("Polyline for map is not valid format")
    #             return None
    #     raise PreventUpdate

    # @app.callback(
    #     Output(
    #         {"id": get_uuid("intersection-data"), "element": "source"},
    #         "value",
    #     ),
    #     Output(
    #         {"id": get_uuid("intersection-data"), "element": "well"},
    #         "value",
    #     ),
    #     Input(get_uuid("leaflet-map1"), "clicked_shape"),
    #     Input(get_uuid("leaflet-map1"), "polyline_points"),
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
    #     if clicked_shape.get("id") in well_set_model.well_names:
    #         return "well", clicked_shape.get("id")
    #     raise PreventUpdate

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


def make_geojson_polyline(positions: List[List[float]]) -> Dict:

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": positions},
                "properties": {"name": "X-line"},
            }
        ],
    }

    # {
    #     "id": name,
    #     "name": name,
    #     "baseLayer": False,
    #     "checked": True,
    #     "action": "update",
    #     "data": [
    #         {
    #             "type": "polyline",
    #             "id": poly_id,
    #             "positions": positions,
    #             "color": "blue",
    #             "tooltip": "polyline",
    #         },
    #         {
    #             "type": "circle",
    #             "center": positions[0],
    #             "radius": 60,
    #             "color": "blue",
    #             "tooltip": "B",
    #         },
    #         {
    #             "type": "circle",
    #             "center": positions[-1],
    #             "radius": 60,
    #             "color": "blue",
    #             "tooltip": "B'",
    #         },
    #     ],
    # }


def get_surface_specification(provider, qualified_address, surface_server):
    surf_meta = surface_server.get_surface_metadata(qualified_address)
    if not surf_meta:
        # This means we need to compute the surface
        surface = provider.get_surface(qualified_address.address)
        if not surface:
            raise ValueError(
                f"Could not get surface for address: {qualified_address.address}"
            )
        surface_server.publish_surface(qualified_address, surface)
        surf_meta = surface_server.get_surface_metadata(qualified_address)

    return {
        "bounds": surf_meta.deckgl_bounds,
        "image": surface_server.encode_partial_url(qualified_address),
        "rotDeg": surf_meta.deckgl_rot_deg,
        "valueRange": [surf_meta.val_min, surf_meta.val_max],
    }, [
        surf_meta.x_min,
        surf_meta.y_min,
        surf_meta.x_max,
        surf_meta.y_max,
    ]


def get_diff_surface_specification(
    provider_a, provider_b, qualified_address, surface_server
):
    surf_meta = surface_server.get_surface_metadata(qualified_address)
    if not surf_meta:
        # This means we need to compute the surface
        surface_a = provider_a.get_surface(qualified_address.address_a)
        surface_b = provider_b.get_surface(qualified_address.address_b)
        if surface_a is not None and surface_b is not None:
            surface = surface_a - surface_b
        surface_server.publish_surface(qualified_address, surface)
        surf_meta = surface_server.get_surface_metadata(qualified_address)

    return {
        "bounds": surf_meta.deckgl_bounds,
        "image": surface_server.encode_partial_url(qualified_address),
        "rotDeg": surf_meta.deckgl_rot_deg,
        "valueRange": [surf_meta.val_min, surf_meta.val_max],
    }, [
        surf_meta.x_min,
        surf_meta.y_min,
        surf_meta.x_max,
        surf_meta.y_max,
    ]
