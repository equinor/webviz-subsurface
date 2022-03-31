import pathlib
import pandas
from dash import Dash
from typing import Dict, List, Optional
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProviderFactory,
    EnsembleSurfaceProviderFactory,
    FaultPolygonsServer,
    SurfaceServer,
)
# TODO: tmp?
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import WellPickProvider
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
        well_pick_file: Optional[str] = None,
    ):
        # TODO: license boundary file should be incorporated into fault
        #  polygon provider, get its own provider or something similar
        super().__init__()
        self._ensemble_paths = webviz_settings.shared_settings["scratch_ensembles"]
        # Surfaces
        self._ensemble_surface_providers = _initialize_surface_providers(webviz_settings, ensembles)
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        self._ensemble_fault_polygons_providers = _initialize_fault_polygon_providers(webviz_settings, ensembles)
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        # License boundary
        self._license_boundary_file = license_boundary_file
        # Wells
        self._well_pick_provider = _initialize_well_picks_providers(well_pick_file)
        self.set_callbacks()

    @property
    def layout(self):
        return main_layout(
            get_uuid=self.uuid,
            ensembles=list(self._ensemble_surface_providers.keys()),
            ensemble_paths=self._ensemble_paths,
        )

    def set_callbacks(self):
        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self._surface_server,
            ensemble_fault_polygons_providers=self._ensemble_fault_polygons_providers,
            fault_polygons_server=self._polygons_server,
            license_boundary_file=self._license_boundary_file,
            well_pick_provider=self._well_pick_provider,
        )


def _initialize_surface_providers(webviz_settings, ensembles):
    surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
    attributes = [m.value for m in MapAttribute]
    return {
        ens: surface_provider_factory.create_from_ensemble_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
            attribute_filter=attributes,
        )
        for ens in ensembles
    }


def _initialize_fault_polygon_providers(webviz_settings, ensembles):
    polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
    return {
        ens: polygon_provider_factory.create_from_ensemble_fault_polygons_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }    


def _initialize_well_picks_providers(well_pick_file):
    if well_pick_file is None:
        return None
    well_pick_table = pandas.read_csv(well_pick_file)
    return WellPickProvider(
        dframe=well_pick_table,
    )
