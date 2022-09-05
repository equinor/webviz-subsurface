from typing import Optional, Dict

import pandas

from webviz_subsurface._providers import EnsembleSurfaceProviderFactory
from webviz_subsurface.plugins._co2_leakage._utilities.general import \
    first_existing_fmu_file_path, fmu_realization_paths, MapAttribute
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import \
    WellPickProvider


def init_map_attribute_names(
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


def init_surface_providers(webviz_settings, ensembles):
    surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
    return {
        ens: surface_provider_factory.create_from_ensemble_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }


def init_fault_polygon_providers(webviz_settings, ensembles):
    from webviz_subsurface._providers import EnsembleFaultPolygonsProviderFactory
    polygon_provider_factory = EnsembleFaultPolygonsProviderFactory.instance()
    return {
        ens: polygon_provider_factory.create_from_ensemble_fault_polygons_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }


def init_well_pick_providers(
    ensemble_roots: Dict[str, str],
    well_pick_rel_path: str,
    map_surface_names_to_well_pick_names: Optional[Dict[str, str]],
) -> Dict[str, WellPickProvider]:
    providers = {}

    for e_name, e_root in ensemble_roots.items():
        realz = fmu_realization_paths(e_root).keys()
        first = first_existing_fmu_file_path(e_root, realz, well_pick_rel_path)
        if first is None:
            continue
        table = pandas.read_csv(first)
        providers[e_name] = WellPickProvider(table, map_surface_names_to_well_pick_names)
    return providers
