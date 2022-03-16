import json
import dash
from dash import callback, Output, Input, State
from dash.exceptions import PreventUpdate
from typing import Callable, Dict, List
from ._utils import MapAttribute
from .layout import LayoutElements, generate_map_layers
from webviz_subsurface._components.deckgl_map.deckgl_map_layers_model import (
    DeckGLMapLayersModel,
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
):
    @callback(
        Output(get_uuid(LayoutElements.DATEINPUT), 'options'),
        Output(get_uuid(LayoutElements.FAULTPOLYGONINPUT), 'options'),
        Input(get_uuid(LayoutElements.ENSEMBLEINPUT), 'value'),
    )
    def set_ensemble(ensemble):
        if ensemble is None:
            return []
        # Dates
        surface_provider = ensemble_surface_providers[ensemble]
        dates = surface_provider.surface_dates_for_attribute(MapAttribute.MaxSaturation.value)
        if dates is None:
            raise NotImplementedError
        dates = [
            dict(label=d, value=d)
            for d in dates
        ]
        # Fault Polygon
        polygon_provider = ensemble_fault_polygons_providers[ensemble]
        # TODO: dl_extracted_faultlines should not be hard-coded
        # TODO: probably want horizons/zones in stratigraphic order
        polygons = polygon_provider.fault_polygons_names_for_attribute("dl_extracted_faultlines")
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
        colormap_address = find_colormap_address(attribute, date)
        polygon_address = find_fault_polygon_address(polygon_name)
        
        surface_provider = ensemble_surface_providers[ensemble]
        polygon_provider = ensemble_fault_polygons_providers[ensemble]

        layers = generate_map_layers()
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
                # "colormap": "https://cdn.jsdelivr.net/gh/kylebarron/deck.gl-raster/assets/colormaps/plasma.png",
                # TODO:
                # "colorMapName": "",
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
        # View
        viewport_bounds = [
            surf_meta.x_min,
            surf_meta.y_min,
            surf_meta.x_max,
            surf_meta.y_max,
        ]
        return layer_model.layers, viewport_bounds


def find_colormap_address(attribute: str, date):
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


def find_fault_polygon_address(polygon_name):
    return SimulatedFaultPolygonsAddress(
        attribute="dl_extracted_faultlines",  # TODO
        name=polygon_name,
        realization=0,
    )


def publish_and_get_surface_metadata(
    surface_server: SurfaceServer,
    surface_provider: EnsembleSurfaceProvider,
    surface_address: SurfaceAddress,
) -> Dict:
    """
    TODO: Nearly direct copy from HK repo
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
