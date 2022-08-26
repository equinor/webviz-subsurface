from dataclasses import dataclass
from typing import Callable, Dict, Optional, List, Tuple, Set, Union, Any

import geojson
import numpy as np
import dash
from dash import callback, Output, Input, State
from dash.exceptions import PreventUpdate
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    SurfaceStatistic, SurfaceAddress
)
# TODO: tmp?
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProvider,
    EnsembleSurfaceProvider,
    FaultPolygonsServer,
    SimulatedFaultPolygonsAddress,
    SimulatedSurfaceAddress,
    SurfaceServer,
    SurfaceMeta,
    StatisticalSurfaceAddress,
)
from . import _plume_extent
from ._formation_alias import (
    surface_name_aliases,
    lookup_surface_alias,
    lookup_fault_polygon_alias,
    lookup_well_pick_alias,
)
from ._surface_publishing import (
    FrequencySurfaceAddress,
    publish_and_get_surface_metadata,
)
from ._utils import MapAttribute, realization_paths, parse_polygon_file, first_existing_file_path
from ._co2volume import (generate_co2_volume_figure, generate_co2_time_containment_figure)
from .layout import LayoutElements, LayoutStyle, LayoutLabels


@dataclass
class _SurfaceData:
    readable_name: str
    color_map_range: Tuple[float, float]
    color_map_name: str
    value_range: Tuple[float, float]
    meta_data: SurfaceMeta
    img_url: str

    @staticmethod
    def from_server(
        server: SurfaceServer,
        provider: EnsembleSurfaceProvider,
        address: Union[SurfaceAddress, FrequencySurfaceAddress],
        color_map_range: Optional[Tuple[float, float]],
        color_map_name: str,
        readable_name: str,
    ):
        surf_meta, img_url = publish_and_get_surface_metadata(server, provider, address)
        value_range = (
            0.0 if np.ma.is_masked(surf_meta.val_min) else surf_meta.val_min,
            0.0 if np.ma.is_masked(surf_meta.val_max) else surf_meta.val_max,
        )
        color_map_range = (
            value_range[0] if color_map_range[0] is None else color_map_range[0],
            value_range[1] if color_map_range[1] is None else color_map_range[1],
        )
        return _SurfaceData(
            readable_name,
            color_map_range,
            color_map_name,
            value_range,
            surf_meta,
            img_url,
        )


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_paths: Dict[str, str],
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: SurfaceServer,
    ensemble_fault_polygons_providers: Dict[str, EnsembleFaultPolygonsProvider],
    fault_polygons_server: FaultPolygonsServer,
    fault_polygon_attribute: str,
    leakage_boundary_relpath: Optional[str],
    co2_containment_relpath: str,
    well_pick_providers: Dict[str, WellPickProvider],
    map_attribute_names: Dict[MapAttribute, str],
    formation_aliases: List[Set[str]],
):
    @callback(
        Output(get_uuid(LayoutElements.REALIZATIONINPUT), "options"),
        Output(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        Output(get_uuid(LayoutElements.ENSEMBLEBARPLOT), "figure"),
        Output(get_uuid(LayoutElements.ENSEMBLETIMELEAKPLOT), "figure"),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
    )
    def set_realizations(ensemble):
        rz_paths = realization_paths(ensemble_paths[ensemble])
        realizations = [
            dict(label=r, value=r)
            for r in sorted(rz_paths.keys())
        ]
        fig0 = generate_co2_volume_figure(
            rz_paths, LayoutStyle.ENSEMBLE_PLOT_HEIGHT, LayoutStyle.ENSEMBLE_PLOT_WIDTH, co2_containment_relpath,
        )
        fig1 = generate_co2_time_containment_figure(
            rz_paths, LayoutStyle.ENSEMBLE_PLOT_HEIGHT, LayoutStyle.ENSEMBLE_PLOT_WIDTH, co2_containment_relpath,
        )
        return realizations, [realizations[0]["value"]], fig0, fig1

    @callback(
        Output(get_uuid(LayoutElements.FORMATION_INPUT), 'options'),
        Output(get_uuid(LayoutElements.FORMATION_INPUT), 'value'),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
        Input(get_uuid(LayoutElements.PROPERTY), 'value'),
        State(get_uuid(LayoutElements.FORMATION_INPUT), 'value'),
    )
    def set_formations(ensemble, prop, current_value):
        if ensemble is None:
            return [], None
        surface_provider = ensemble_surface_providers[ensemble]
        # Map
        prop_name = _property_origin(MapAttribute(prop), map_attribute_names)
        surfaces = surface_name_aliases(surface_provider, prop_name)
        # Formation names
        formations = [{"label": v.title(), "value": v} for v in surfaces]
        picked_formation = None
        if len(formations) != 0:
            if any(fmt["value"] == current_value for fmt in formations):
                picked_formation = dash.no_update
            else:
                picked_formation = formations[0]["value"]
        return formations, picked_formation

    @callback(
        Output(get_uuid(LayoutElements.DATEINPUT), 'marks'),
        Output(get_uuid(LayoutElements.DATEINPUT), 'value'),
        Output(get_uuid(LayoutElements.DATE_STORE), "data"),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
    )
    def set_dates(ensemble):
        if ensemble is None:
            return [], None, []
        # Dates
        surface_provider = ensemble_surface_providers[ensemble]
        att_name = map_attribute_names[MapAttribute.MAX_SGAS]
        date_list = surface_provider.surface_dates_for_attribute(att_name)
        if date_list is None:
            dates = {}
            initial_date = dash.no_update
        else:
            dates = {
                # Regarding tooltips: https://github.com/plotly/dash/issues/1846
                i: {
                    "label": f"{d[:4]}",
                    "style": {"writingMode": "vertical-rl"},
                }
                for i, d in enumerate(date_list)
            }
            initial_date = max(dates.keys())
        return dates, initial_date, date_list

    @callback(
        Output(get_uuid(LayoutElements.DATE_INPUT_WRAPPER), "style"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
    )
    def toggle_date_slider(attribute):
        if MapAttribute(attribute) == MapAttribute.MIGRATION_TIME:
            return {"display": "none"}
        else:
            return {}

    @callback(
        Output(get_uuid(LayoutElements.LAST_STATISTIC_STORE), "data"),
        Input(get_uuid(LayoutElements.STATISTIC_INPUT), "value"),
    )
    def store_statistic(value):
        if value:
            return value
        return dash.no_update

    @callback(
        Output(get_uuid(LayoutElements.STATISTIC_INPUT), "disabled"),
        Output(get_uuid(LayoutElements.STATISTIC_INPUT), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        State(get_uuid(LayoutElements.LAST_STATISTIC_STORE), "data"),
    )
    def toggle_statistics(realizations, attribute, last_statistic):
        if len(realizations) <= 1:
            return True, None
        elif MapAttribute(attribute) in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
            return True, None
        else:
            if last_statistic is None:
                last_statistic = SurfaceStatistic.MEAN
            return False, last_statistic

    @callback(
        Output(get_uuid(LayoutElements.COLOR_RANGE_STORE), "data"),
        Output(get_uuid(LayoutElements.COLOR_RANGE_MIN_VALUE), "disabled"),
        Output(get_uuid(LayoutElements.COLOR_RANGE_MAX_VALUE), "disabled"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MIN_AUTO), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MIN_VALUE), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MAX_AUTO), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_MAX_VALUE), "value"),
    )
    def set_color_range_data(min_auto, min_val, max_auto, max_val):
        return (
            [
                min_val if len(min_auto) == 0 else None,
                max_val if len(max_auto) == 0 else None,
            ],
            len(min_auto) == 1,
            len(max_auto) == 1,
        )

    @callback(
        Output(get_uuid(LayoutElements.PLUME_CONTOUR_STORE), "data"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        Input(get_uuid(LayoutElements.PLUME_THRESHOLD), "value"),
        Input(get_uuid(LayoutElements.PLUME_SMOOTHING), "value"),
    )
    def set_plume_contour_data(
        attribute,
        threshold,
        smoothing,
    ):
        if attribute is None:
            return None
        attribute = MapAttribute(attribute)
        if attribute not in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
            return None
        return {
            "property": _property_origin(attribute, map_attribute_names),
            "threshold": threshold,
            "smoothing": smoothing,
        }

    @callback(
        Output(get_uuid(LayoutElements.DECKGLMAP), "layers"),
        Output(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        Input(get_uuid(LayoutElements.DATEINPUT), "value"),
        Input(get_uuid(LayoutElements.FORMATION_INPUT), "value"),
        Input(get_uuid(LayoutElements.REALIZATIONINPUT), "value"),
        Input(get_uuid(LayoutElements.STATISTIC_INPUT), "value"),
        Input(get_uuid(LayoutElements.COLORMAP_INPUT), "value"),
        Input(get_uuid(LayoutElements.COLOR_RANGE_STORE), "data"),
        Input(get_uuid(LayoutElements.PLUME_CONTOUR_STORE), "data"),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
        State(get_uuid(LayoutElements.DATE_STORE), "data"),
        State(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
    )
    def update_map_attribute(
        attribute,
        date,
        formation,
        realization,
        statistic,
        color_map_name,
        color_map_range,
        contour_data,
        ensemble,
        date_list,
        current_bounds,
    ):
        attribute = MapAttribute(attribute)
        if len(realization) == 0:
            raise PreventUpdate
        if ensemble is None:
            raise PreventUpdate
        if attribute != MapAttribute.MIGRATION_TIME and date is None:
            raise PreventUpdate
        date = str(date_list[date])
        # Look up formation aliases
        surface_name = lookup_surface_alias(
            formation_aliases,
            formation,
            ensemble_surface_providers[ensemble],
            _property_origin(attribute, map_attribute_names),
        )
        polygon_name = lookup_fault_polygon_alias(
            formation_aliases, formation, ensemble_fault_polygons_providers[ensemble], fault_polygon_attribute
        )
        well_pick_horizon = lookup_well_pick_alias(
            formation_aliases, formation, well_pick_providers[ensemble]
        )
        # Surface
        if surface_name is None:
            surf_data = None
        elif len(realization) == 0:
            surf_data = None
        else:
            surf_data = _SurfaceData.from_server(
                server=surface_server,
                provider=ensemble_surface_providers[ensemble],
                address=_derive_surface_address(
                    surface_name,
                    attribute,
                    date,
                    realization,
                    map_attribute_names,
                    statistic,
                    contour_data,
                ),
                color_map_range=color_map_range,
                color_map_name=color_map_name,
                readable_name=_readable_name(attribute),
            )
        # Plume polygon
        plume_polygon = None
        if contour_data is not None:
            plume_polygon = _get_plume_polygon(
                ensemble_surface_providers[ensemble],
                realization,
                surface_name,
                date,
                contour_data,
            )
        # Create layers and view bounds
        layers, viewport_bounds = create_map_layers(
            surface_data=surf_data,
            fault_polygon_url=_extract_fault_polygon_url(
                server=fault_polygons_server,
                provider=ensemble_fault_polygons_providers[ensemble],
                polygon_name=polygon_name,
                realization=realization,
                fault_polygon_attribute=fault_polygon_attribute,
            ),
            license_boundary_file=first_existing_file_path(
                ensemble_paths[ensemble], realization, leakage_boundary_relpath
            ),
            well_pick_provider=well_pick_providers[ensemble],
            well_pick_horizon=well_pick_horizon,
            plume_extent_data=plume_polygon,
        )
        if tuple(current_bounds) != LayoutStyle.INITIAL_BOUNDS:
            viewport_bounds = dash.no_update
        return layers, viewport_bounds


def create_map_layers(
    surface_data: Optional[_SurfaceData],
    fault_polygon_url: Optional[str],
    license_boundary_file: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    well_pick_horizon: Optional[str],
    plume_extent_data: Optional[geojson.FeatureCollection],
) -> Tuple[List[Dict], List[float]]:
    layers = []
    viewport_bounds = dash.no_update
    if surface_data is not None:
        # Update ColormapLayer
        layers.append({
            "@@type": "ColormapLayer",
            "name": surface_data.readable_name,
            "id": LayoutElements.COLORMAPLAYER,
            "image": surface_data.img_url,
            "bounds": surface_data.meta_data.deckgl_bounds,
            "valueRange": surface_data.value_range,
            "colorMapRange": surface_data.color_map_range,
            "colorMapName": surface_data.color_map_name,
            "rotDeg": surface_data.meta_data.deckgl_rot_deg,
        })
        viewport_bounds = [
            surface_data.meta_data.x_min,
            surface_data.meta_data.y_min,
            surface_data.meta_data.x_max,
            surface_data.meta_data.y_max,
        ]
    if fault_polygon_url is not None:
        layers.append({
            "@@type": "FaultPolygonsLayer",
            "name": "Fault Polygons",
            "id": LayoutElements.FAULTPOLYGONSLAYER,
            "data": fault_polygon_url,
        })
    if license_boundary_file is not None:
        layers.append({
            "@@type": "FaultPolygonsLayer",
            "name": LayoutLabels.LICENSE_BOUNDARY_LAYER,
            "id": LayoutElements.LICENSEBOUNDARYLAYER,
            "data": parse_polygon_file(license_boundary_file),
        })
    if well_pick_provider is not None:
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Well Picks",
            "id": LayoutElements.WELLPICKSLAYER,
            "data": dict(
                well_pick_provider.get_geojson(
                    well_pick_provider.well_names(), well_pick_horizon
                )
            ),
        })
    if plume_extent_data is not None:
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Plume Contours",
            "id": LayoutElements.PLUME_POLYGON_LAYER,
            "data": dict(plume_extent_data),
            "lineWidthMinPixels": 2,
            "getLineColor": [150, 150, 150, 255],
        })
    return layers, viewport_bounds


def _property_origin(attribute: MapAttribute, map_attribute_names: Dict[MapAttribute, str]):
    if attribute in map_attribute_names:
        return map_attribute_names[attribute]
    elif attribute == MapAttribute.SGAS_PLUME:
        return map_attribute_names[MapAttribute.MAX_SGAS]
    elif attribute == MapAttribute.AMFG_PLUME:
        return map_attribute_names[MapAttribute.MAX_AMFG]
    else:
        raise AssertionError(f"No origin defined for property: {attribute}")


def _extract_fault_polygon_url(
    server: FaultPolygonsServer,
    provider: EnsembleFaultPolygonsProvider,
    polygon_name: Optional[str],
    realization: List[int],
    fault_polygon_attribute: str,
) -> Optional[str]:
    if polygon_name is None:
        return None
    if len(realization) == 0:
        return None
    # This always returns the url corresponding to the first realization
    address = _derive_fault_polygon_address(polygon_name, realization[0], fault_polygon_attribute)
    return server.encode_partial_url(
        provider_id=provider.provider_id(),
        fault_polygons_address=address,
    )


def _readable_name(attribute: MapAttribute):
    unit = ""
    if attribute == MapAttribute.MIGRATION_TIME:
        unit = " [year]"
    elif attribute in (MapAttribute.AMFG_PLUME, MapAttribute.SGAS_PLUME):
        unit = " [# real.]"
    return f"{attribute.value}{unit}"


def _derive_surface_address(
    surface_name: str,
    attribute: MapAttribute,
    date: Optional[str],
    realization: List[int],
    map_attribute_names: Dict[MapAttribute, str],
    statistic: str,
    contour_data: Optional[Dict[str, Any]],
):
    date = None if attribute == MapAttribute.MIGRATION_TIME else date
    if attribute in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
        return FrequencySurfaceAddress(
            name=surface_name,
            datestr=date,
            realizations=realization,
            basis_attribute=(
                map_attribute_names[MapAttribute.MAX_SGAS]
                if attribute == MapAttribute.SGAS_PLUME
                else map_attribute_names[MapAttribute.MAX_AMFG]
            ),
            threshold=contour_data["threshold"] if contour_data else 0.0,
            smoothing=contour_data["smoothing"] if contour_data else 0.0,
        )
    elif len(realization) == 1:
        return SimulatedSurfaceAddress(
            attribute=map_attribute_names[attribute],
            name=surface_name,
            datestr=date,
            realization=realization[0],
        )
    else:
        return StatisticalSurfaceAddress(
            attribute=map_attribute_names[attribute],
            name=surface_name,
            datestr=date,
            statistic=SurfaceStatistic(statistic),
            realizations=realization,
        )


def _derive_fault_polygon_address(polygon_name, realization, fault_polygon_attribute):
    return SimulatedFaultPolygonsAddress(
        attribute=fault_polygon_attribute,
        name=polygon_name,
        realization=realization,
    )


def _get_plume_polygon(
    surface_provider: EnsembleSurfaceProvider,
    realizations: List[int],
    surface_name: str,
    datestr: str,
    contour_data: Dict[str, Any],
) -> Optional[geojson.FeatureCollection]:
    surface_attribute = contour_data["property"]
    threshold = contour_data["threshold"]
    smoothing = contour_data["smoothing"]
    if (
        surface_attribute is None
        or len(realizations) == 0
        or threshold is None
        or threshold <= 0
    ):
        return None
    surfaces = [
        surface_provider.get_surface(SimulatedSurfaceAddress(
            attribute=surface_attribute,
            name=surface_name,
            datestr=datestr,
            realization=r,
        ))
        for r in realizations
    ]
    surfaces = [s for s in surfaces if s is not None]
    if len(surfaces) == 0:
        return None
    return _plume_extent.plume_polygon(
        surfaces,
        threshold,
        smoothing=smoothing,
        simplify_factor=0.12 * smoothing,  # Experimental
    )
