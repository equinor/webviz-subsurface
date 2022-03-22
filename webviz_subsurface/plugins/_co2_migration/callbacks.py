import json
import dash
from dash import callback, Output, Input, State
from dash.exceptions import PreventUpdate
from typing import Callable, Dict, List, Optional
from ._utils import MapAttribute, FAULT_POLYGON_ATTRIBUTE
from .layout import LayoutElements
from webviz_subsurface._components.deckgl_map.deckgl_map_layers_model import (
    DeckGLMapLayersModel,
)
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    FaultPolygonsLayer,
)
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProvider,
    EnsembleSurfaceProvider,
    FaultPolygonsServer,
    QualifiedSurfaceAddress,
    SimulatedFaultPolygonsAddress,
    SimulatedSurfaceAddress,
    SurfaceAddress,
    SurfaceServer,
)


def plugin_callbacks(
    get_uuid: Callable,
    ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
    surface_server: SurfaceServer,
    ensemble_fault_polygons_providers: Dict[str, EnsembleFaultPolygonsProvider],
    fault_polygons_server: FaultPolygonsServer,
    license_boundary_file: Optional[str],
):
    @callback(
        Output(get_uuid(LayoutElements.DATEINPUT), 'marks'),
        Output(get_uuid(LayoutElements.FAULTPOLYGONINPUT), 'options'),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
    )
    def set_ensemble(ensemble):
        if ensemble is None:
            return [], []
        # Dates
        surface_provider = ensemble_surface_providers[ensemble]
        dates = surface_provider.surface_dates_for_attribute(MapAttribute.MaxSaturation.value)
        if dates is None:
            dates = []
        dates = {
            # TODO: handle dates using some utility tool instead?
            # TODO: using date as value is convenient, but won't reflect the correct position of the mark
            int(d): '' if i > 0 and i < len(dates) - 1 else f"{d[:4]}.{d[4:6]}.{d[6:]}"
            for i, d in enumerate(dates)
        }
        # Fault Polygon
        polygon_provider = ensemble_fault_polygons_providers[ensemble]
        # TODO: ideally want horizons/zones in stratigraphic order?
        polygons = polygon_provider.fault_polygons_names_for_attribute(FAULT_POLYGON_ATTRIBUTE)
        polygons = [
            dict(label=p, value=p)
            for p in polygons
        ]
        return dates, polygons

    @callback(
        Output(get_uuid(LayoutElements.DECKGLMAP), "layers"),
        Output(get_uuid(LayoutElements.DECKGLMAP), "bounds"),
        Input(get_uuid(LayoutElements.PROPERTY), "value"),
        Input(get_uuid(LayoutElements.DATEINPUT), "value"),
        Input(get_uuid(LayoutElements.FAULTPOLYGONINPUT), "value"),
        State(get_uuid(LayoutElements.ENSEMBLEINPUT), "value"),
    )
    def update_map_attribute(attribute, date, polygon_name, ensemble):
        if ensemble is None:
            raise PreventUpdate
        if MapAttribute(attribute) == MapAttribute.MaxSaturation and date is None:
            raise PreventUpdate
        date = str(date)

        layer_model, viewport_bounds = create_layer_model(
            surface_server=surface_server,
            surface_provider=ensemble_surface_providers[ensemble],
            colormap_address=derive_colormap_address(attribute, date),
            fault_polygons_server=fault_polygons_server,
            polygon_provider=ensemble_fault_polygons_providers[ensemble],
            polygon_address=derive_fault_polygon_address(polygon_name),
            license_boundary_file=license_boundary_file,
        )
        return layer_model.layers, viewport_bounds


def create_layer_model(
    surface_server: SurfaceServer,
    surface_provider: EnsembleSurfaceProvider,
    colormap_address: SimulatedSurfaceAddress,
    fault_polygons_server: FaultPolygonsServer,
    polygon_provider: EnsembleFaultPolygonsProvider,
    polygon_address: SimulatedFaultPolygonsAddress,
    license_boundary_file: Optional[str],
) -> DeckGLMapLayersModel:
    # TODO: Using DeckGLMapLayersModel seems a bit unnecessary here,
    #  but we might want to use it for consistency with other plugins
    layers = generate_map_layers(include_license_boundary=license_boundary_file is not None)
    layers = [json.loads(lay) for lay in layers]
    layer_model = DeckGLMapLayersModel(layers)
    # Update ColormapLayer
    surf_meta, img_url  = publish_and_get_surface_metadata(surface_server, surface_provider, colormap_address)
    layer_model.update_layer_by_id(
        layer_id=LayoutElements.COLORMAPLAYER,
        layer_data={
            "image": img_url,
            "bounds": surf_meta.deckgl_bounds,
            "rotDeg": surf_meta.deckgl_rot_deg,
            "valueRange": [surf_meta.val_min, surf_meta.val_max],
            "colorMapRange": [surf_meta.val_min, surf_meta.val_max],
        }
    )
    # Update FaultPolygonLayer
    layer_model.update_layer_by_id(
        layer_id=LayoutElements.FAULTPOLYGONSLAYER,
        layer_data={
            "data": fault_polygons_server.encode_partial_url(
                provider_id=polygon_provider.provider_id(),
                fault_polygons_address=polygon_address,
            ),
        },
    )
    # Update License boundary
    if license_boundary_file is not None:
        layer_model.update_layer_by_id(
            layer_id=LayoutElements.LICENSEBOUNDARYLAYER,
            layer_data={
                "data": parse_polygon_file(license_boundary_file)
            }
        )
    # View-port
    viewport_bounds = [
        surf_meta.x_min,
        surf_meta.y_min,
        surf_meta.x_max,
        surf_meta.y_max,
    ]
    return layer_model, viewport_bounds


def parse_polygon_file(filename: str):
    import numpy as np
    xyz = np.genfromtxt(filename, skip_header=1, delimiter=",")
    as_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": xyz[:, :2].tolist(),
                }
            }
        ]
    }
    return as_geojson


def derive_colormap_address(attribute: str, date):
    attribute = MapAttribute(attribute)
    if attribute == MapAttribute.MigrationTime:
        return SimulatedSurfaceAddress(
            attribute=MapAttribute.MigrationTime.value,
            name="all",
            datestr=None,
            realization=0,  # TODO
        )
    elif attribute == MapAttribute.MaxSaturation:
        return SimulatedSurfaceAddress(
            attribute=MapAttribute.MaxSaturation.value,
            name="all",
            datestr=date,
            realization=0,  # TODO
        )
    else:
        raise NotImplementedError


def derive_fault_polygon_address(polygon_name):
    return SimulatedFaultPolygonsAddress(
        attribute=FAULT_POLYGON_ATTRIBUTE,
        name=polygon_name,
        realization=0,
    )


def publish_and_get_surface_metadata(
    surface_server: SurfaceServer,
    surface_provider: EnsembleSurfaceProvider,
    surface_address: SurfaceAddress,
) -> Dict:
    """
    Nearly direct copy from MapViewerFMU
    """
    provider_id: str = surface_provider.provider_id()
    qualified_address = QualifiedSurfaceAddress(provider_id, surface_address)
    surf_meta = surface_server.get_surface_metadata(qualified_address)
    if not surf_meta:
        # This means we need to compute the surface
        surface = surface_provider.get_surface(address=surface_address)
        if not surface:
            raise ValueError(
                f"Could not get surface for address: {surface_address}"
            )
        surface_server.publish_surface(qualified_address, surface)
        surf_meta = surface_server.get_surface_metadata(qualified_address)
    return surf_meta, surface_server.encode_partial_url(qualified_address)


def generate_map_layers(include_license_boundary: bool):
    layers = [
        ColormapLayer(uuid=LayoutElements.COLORMAPLAYER).to_json(),
        FaultPolygonsLayer(uuid=LayoutElements.FAULTPOLYGONSLAYER).to_json(),
    ]
    if include_license_boundary:
        layers.append(
            # TODO: May want a new class for license boundary, even though
            #  it will be similar/identical to FaultPolygonsLayer
            FaultPolygonsLayer(
                uuid=LayoutElements.LICENSEBOUNDARYLAYER,
                name="License boundary",  # TODO: name definition in layout.py or something
            ).to_json()
        )
    return layers
