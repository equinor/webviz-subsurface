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
from ._utils import MapAttribute, realization_paths, first_existing_file_path


class CO2Leakage(WebvizPluginABC):
    """
    Plugin for analyzing CO2 leakage potential across multiple realizations in an FMU
    ensemble

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`boundary_relpath`:** Path to a polygon representing the containment area
    * **`well_pick_relpath`:** Path to a file containing well picks
    * **`co2_containment_relpath`:** Path to a table of co2 containment data (amount of
        CO2 outside/inside a boundary)
    * **`fault_polygon_attribute`:** Polygons with this attribute are used as fault
        polygons
    * **`map_attribute_names`:** Dictionary for overriding the default mapping between
        attributes visualized by the plugin, and the attributes names used by
        EnsembleSurfaceProvider
    * **`formation_aliases`:** List of formation aliases. Relevant when the formation
        name convention of e.g. well picks is different from that of surface maps

    ---

    TODO: Elaborate on arguments above
    """
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        boundary_relpath: Optional[str] = "share/results/polygons/leakage_boundary.csv",
        well_pick_relpath: Optional[str] = "share/results/wells/well_picks.csv",
        co2_containment_relpath: Optional[str] = "share/results/tables/co2_volumes.csv",
        fault_polygon_attribute: Optional[str] = "dl_extracted_faultlines",
        map_attribute_names: Optional[Dict[str, str]] = None,
        formation_aliases: Optional[List[List[str]]] = None,
    ):
        super().__init__()
        self._ensemble_paths = webviz_settings.shared_settings["scratch_ensembles"]
        self._map_attribute_names = _init_map_attribute_names(map_attribute_names)
        # Surfaces
        self._ensemble_surface_providers = _init_surface_providers(
            webviz_settings, ensembles
        )
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        self._ensemble_fault_polygons_providers = _init_fault_polygon_providers(
            webviz_settings, ensembles
        )
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        self._formation_aliases = [set(f) for f in formation_aliases or []]
        self._fault_polygon_attribute = fault_polygon_attribute
        # License boundary
        self._boundary_rel_path = boundary_relpath
        # Well picks
        self._well_pick_providers = _init_well_pick_providers(
            self._ensemble_paths, well_pick_relpath
        )
        # CO2 containment
        self._co2_containment_relpath = co2_containment_relpath
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
            fault_polygon_attribute=self._fault_polygon_attribute,
            fault_polygons_server=self._polygons_server,
            leakage_boundary_relpath=self._boundary_rel_path,
            co2_containment_relpath=self._co2_containment_relpath,
            well_pick_providers=self._well_pick_providers,
            map_attribute_names=self._map_attribute_names,
            formation_aliases=self._formation_aliases,
        )


def _init_map_attribute_names(
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


def _init_surface_providers(webviz_settings, ensembles):
    surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
    return {
        ens: surface_provider_factory.create_from_ensemble_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }


def _init_fault_polygon_providers(webviz_settings, ensembles):
    polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
    return {
        ens: polygon_provider_factory.create_from_ensemble_fault_polygons_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }    


def _init_well_pick_providers(
    ensemble_roots: Dict[str, str],
    well_pick_rel_path: str,
) -> Dict[str, WellPickProvider]:
    providers = {}

    for e_name, e_root in ensemble_roots.items():
        realz = realization_paths(e_root).keys()
        first = first_existing_file_path(e_root, realz, well_pick_rel_path)
        if first is None:
            continue
        table = pandas.read_csv(first)
        providers[e_name] = WellPickProvider(table)
    return providers
