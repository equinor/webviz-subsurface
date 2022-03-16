import pathlib
from dash import Dash
from typing import Dict, List
from webviz_config import WebvizPluginABC
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProviderFactory,
    EnsembleSurfaceProviderFactory,
    FaultPolygonsServer,
    SurfaceServer,
)
from .layout import main_layout
from .callbacks import plugin_callbacks
from ._utils import MapAttribute


class CO2Migration(WebvizPluginABC):
    def __init__(self, app: Dash, ensemble_paths: List[str]):
        # TODO: ensemble_paths should be replaced by "shared_settings"?
        super().__init__()
        # Surfaces
        surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
        attributes = [m.value for m in MapAttribute]
        self._ensemble_surface_providers = {
            pathlib.Path(ens).name: surface_provider_factory.create_from_ensemble_surface_files(
                ens,
                attribute_filter=attributes,
            )
            for ens in ensemble_paths
        }
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
        self._ensemble_fault_polygons_providers = {
            pathlib.Path(ens).name: polygon_provider_factory.create_from_ensemble_fault_polygons_files(ens)
            for ens in ensemble_paths
        }
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        self.set_callbacks()

    @property
    def layout(self):
        return main_layout(
            get_uuid=self.uuid,
            ensembles=list(self._ensemble_surface_providers.keys()),
        )

    def set_callbacks(self):
        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self._surface_server,
            ensemble_fault_polygons_providers=self._ensemble_fault_polygons_providers,
            fault_polygons_server=self._polygons_server,
        )
