from dataclasses import dataclass
from typing import Dict, Tuple, Union, Optional, List, Any

import geojson
import numpy as np

from webviz_subsurface._providers import SurfaceMeta, SurfaceServer, \
    EnsembleSurfaceProvider, SurfaceAddress, SimulatedSurfaceAddress, \
    StatisticalSurfaceAddress, FaultPolygonsServer, EnsembleFaultPolygonsProvider, \
    SimulatedFaultPolygonsAddress
from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import \
    SurfaceStatistic
from webviz_subsurface.plugins._co2_leakage._utilities import plume_extent
from webviz_subsurface.plugins._co2_leakage._utilities.surface_publishing import \
    TruncatedSurfaceAddress, publish_and_get_surface_metadata
from webviz_subsurface.plugins._co2_leakage._utilities.general import MapAttribute, \
    parse_polygon_file
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import \
    WellPickProvider


def property_origin(
    attribute: MapAttribute, map_attribute_names: Dict[MapAttribute, str]
):
    if attribute in map_attribute_names:
        return map_attribute_names[attribute]
    elif attribute == MapAttribute.SGAS_PLUME:
        return map_attribute_names[MapAttribute.MAX_SGAS]
    elif attribute == MapAttribute.AMFG_PLUME:
        return map_attribute_names[MapAttribute.MAX_AMFG]
    else:
        raise AssertionError(f"No origin defined for property: {attribute}")


@dataclass
class SurfaceData:
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
        address: Union[SurfaceAddress, TruncatedSurfaceAddress],
        color_map_range: Tuple[Optional[float], Optional[float]],
        color_map_name: str,
        readable_name_: str,
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
        return SurfaceData(
            readable_name_,
            color_map_range,
            color_map_name,
            value_range,
            surf_meta,
            img_url,
        )


def derive_surface_address(
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
        basis = (
            MapAttribute.MAX_SGAS
            if attribute == MapAttribute.SGAS_PLUME
            else MapAttribute.MAX_AMFG
        )
        return TruncatedSurfaceAddress(
            name=surface_name,
            datestr=date,
            realizations=realization,
            basis_attribute=map_attribute_names[basis],
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


def readable_name(attribute: MapAttribute):
    unit = ""
    if attribute == MapAttribute.MIGRATION_TIME:
        unit = " [year]"
    elif attribute in (MapAttribute.AMFG_PLUME, MapAttribute.SGAS_PLUME):
        unit = " [# real.]"
    return f"{attribute.value}{unit}"


def get_plume_polygon(
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
    return plume_extent.plume_polygons(
        surfaces,
        threshold,
        smoothing=smoothing,
        simplify_factor=0.12 * smoothing,  # Experimental
    )


def create_map_layers(
    formation: str,
    surface_data: Optional[SurfaceData],
    fault_polygon_url: Optional[str],
    license_boundary_file: Optional[str],
    well_pick_provider: Optional[WellPickProvider],
    plume_extent_data: Optional[geojson.FeatureCollection],
) -> Tuple[List[Dict], Optional[List[float]]]:
    layers = []
    viewport_bounds = None
    if surface_data is not None:
        # Update ColormapLayer
        layers.append({
            "@@type": "ColormapLayer",
            "name": surface_data.readable_name,
            "id": "colormap-layer",
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
            "id": "fault-polygons-layer",
            "data": fault_polygon_url,
        })
    if license_boundary_file is not None:
        layers.append({
            "@@type": "FaultPolygonsLayer",
            "name": "Containment Boundary",
            "id": "license-boundary-layer",
            "data": parse_polygon_file(license_boundary_file),
        })
    if well_pick_provider is not None:
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Well Picks",
            "id": "well-picks-layer",
            "data": dict(
                well_pick_provider.get_geojson(
                    well_pick_provider.well_names(), formation
                )
            ),
        })
    if plume_extent_data is not None:
        layers.append({
            "@@type": "GeoJsonLayer",
            "name": "Plume Contours",
            "id": "plume-polygon-layer",
            "data": dict(plume_extent_data),
            "lineWidthMinPixels": 2,
            "getLineColor": [150, 150, 150, 255],
        })
    return layers, viewport_bounds


def extract_fault_polygon_url(
    server: FaultPolygonsServer,
    provider: EnsembleFaultPolygonsProvider,
    polygon_name: Optional[str],
    realization: List[int],
    fault_polygon_attribute: str,
    map_surface_names_to_fault_polygons: Dict[str, str],
) -> Optional[str]:
    if polygon_name is None:
        return None
    if len(realization) == 0:
        return None
    # NB! This always returns the url corresponding to the first realization
    address = SimulatedFaultPolygonsAddress(
        attribute=fault_polygon_attribute,
        name=map_surface_names_to_fault_polygons.get(polygon_name, polygon_name),
        realization=realization[0],
    )
    return server.encode_partial_url(
        provider_id=provider.provider_id(),
        fault_polygons_address=address,
    )
