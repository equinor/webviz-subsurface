import pathlib
from dash import Dash
from typing import Dict, List, Optional
from webviz_config import WebvizPluginABC, WebvizSettings
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
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        license_boundary_file: Optional[str] = None,
    ):
        # TODO: license boundary file should be incorporated into fault
        #  polygon provider, or get its own provider?
        super().__init__()
        # Surfaces
        surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
        attributes = [m.value for m in MapAttribute]
        self._ensemble_surface_providers = {
            ens: surface_provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens],
                attribute_filter=attributes,
            )
            for ens in ensembles
        }
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
        self._ensemble_fault_polygons_providers = {
            ens: polygon_provider_factory.create_from_ensemble_fault_polygons_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens],
            )
            for ens in ensembles
        }
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        self._license_boundary_file = license_boundary_file
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
            license_boundary_file=self._license_boundary_file,
        )
