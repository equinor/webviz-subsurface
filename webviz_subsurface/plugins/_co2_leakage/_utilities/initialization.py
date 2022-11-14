from typing import Dict, List, Optional

from webviz_config import WebvizSettings

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    EnsembleSurfaceProviderFactory,
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)
from webviz_subsurface._utils.webvizstore_functions import read_csv
from webviz_subsurface.plugins._co2_leakage._utilities.generic import MapAttribute
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)


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
    return {MapAttribute(key): value for key, value in mapping.items()}


def init_surface_providers(
    webviz_settings: WebvizSettings,
    ensembles: List[str],
) -> Dict[str, EnsembleSurfaceProvider]:
    surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
    return {
        ens: surface_provider_factory.create_from_ensemble_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
        )
        for ens in ensembles
    }


def init_well_pick_provider(
    well_pick_path: Optional[str],
    map_surface_names_to_well_pick_names: Optional[Dict[str, str]],
) -> Optional[WellPickProvider]:
    if well_pick_path is None:
        return None
    try:
        return WellPickProvider(
            read_csv(well_pick_path), map_surface_names_to_well_pick_names
        )
    except OSError:
        return None


def init_co2_containment_table_providers(
    ensemble_roots: Dict[str, str],
    table_rel_path: str,
) -> Dict[str, EnsembleTableProvider]:
    return {
        ens: (
            EnsembleTableProviderFactory.instance().create_from_per_realization_csv_file(
                ens_path, table_rel_path
            )
        )
        for ens, ens_path in ensemble_roots.items()
    }
