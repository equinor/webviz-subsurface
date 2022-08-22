from typing import List, Optional, Dict
import pandas
from dash import Dash
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
        map_attribute_names: Optional[Dict[str, str]] = None,
        formation_aliases: Optional[List[List[str]]] = None,
    ):
        # TMP
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning)
        # ---
        super().__init__()
        self._ensemble_paths = webviz_settings.shared_settings["scratch_ensembles"]
        self._map_attribute_names = _initialize_map_attribute_names(map_attribute_names)
        # Surfaces
        self._ensemble_surface_providers = _initialize_surface_providers(webviz_settings, ensembles)
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        self._ensemble_fault_polygons_providers = _initialize_fault_polygon_providers(webviz_settings, ensembles)
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        self._formation_aliases = [set(f) for f in formation_aliases or []]
        # License boundary
        # TODO: may want to expose license boundary via a provider, but need
        #  standardization on its location first
        self._license_boundary_file = license_boundary_file
        # Wells
        # TODO: this does not support well picks differing between realizations
        self._well_pick_provider = _initialize_well_picks_providers(well_pick_file)
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
            ensemble_paths=self._ensemble_paths,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self._surface_server,
            ensemble_fault_polygons_providers=self._ensemble_fault_polygons_providers,
            fault_polygons_server=self._polygons_server,
            license_boundary_file=self._license_boundary_file,
            well_pick_provider=self._well_pick_provider,
            map_attribute_names=self._map_attribute_names,
            formation_aliases=self._formation_aliases,
        )


def _initialize_map_attribute_names(
    mapping: Optional[Dict[str, str]]
) -> Dict[MapAttribute, str]:
    if mapping is None:
        # Based on name convention of xtgeoapp_grd3dmaps:
        return {
            MapAttribute.MIGRATION_TIME: "MigrationTime",
            MapAttribute.MAX_SGAS: "max_SGAS",
            MapAttribute.MAX_AMFG: "max_AMFG",
        }
    else:
        return {MapAttribute(key): value for key, value in mapping.items()}


def _initialize_surface_providers(webviz_settings, ensembles):
    surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
    return {
        ens: surface_provider_factory.create_from_ensemble_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
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
