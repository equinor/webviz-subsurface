import logging
import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional

from webviz_config import WebvizSettings

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    EnsembleSurfaceProviderFactory,
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)
from webviz_subsurface._utils.webvizstore_functions import read_csv
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import (
    read_zone_options,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    GraphSource,
    MapAttribute,
)
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)

LOGGER = logging.getLogger(__name__)


def init_map_attribute_names(
    mapping: Optional[Dict[str, str]]
) -> Dict[MapAttribute, str]:
    if mapping is None:
        # Based on name convention of xtgeoapp_grd3dmaps:
        return {
            MapAttribute.MIGRATION_TIME: "migrationtime",
            MapAttribute.MAX_SGAS: "max_sgas",
            MapAttribute.MAX_AMFG: "max_amfg",
            # MapAttribute.MASS: "mass_total",  # NBNB-AS: Or sum_mass_total
            MapAttribute.MASS: "mass",
            MapAttribute.DISSOLVED: "dissolved_mass",
            MapAttribute.FREE: "free_mass",
        }
    return {MapAttribute[key]: value for key, value in mapping.items()}


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


def init_table_provider(
    ensemble_roots: Dict[str, str],
    table_rel_path: str,
) -> Dict[str, EnsembleTableProvider]:
    providers = {}
    factory = EnsembleTableProviderFactory.instance()
    for ens, ens_path in ensemble_roots.items():
        try:
            providers[ens] = factory.create_from_per_realization_csv_file(
                ens_path, table_rel_path
            )
        except (KeyError, ValueError) as exc:
            LOGGER.warning(
                f'Did not load "{table_rel_path}" for ensemble "{ens}" with error {exc}'
            )
    return providers


def init_zone_options(
    ensemble_roots: Dict[str, str],
    mass_table: Dict[str, EnsembleTableProvider],
    actual_volume_table: Dict[str, EnsembleTableProvider],
    ensemble_provider: Dict[str, EnsembleSurfaceProvider],
) -> Dict[str, Dict[str, List[str]]]:
    options: Dict[str, Dict[str, List[str]]] = {}
    for ens in ensemble_roots.keys():
        options[ens] = {}
        real = ensemble_provider[ens].realizations()[0]
        for source, table in zip(
            [GraphSource.CONTAINMENT_MASS, GraphSource.CONTAINMENT_ACTUAL_VOLUME],
            [mass_table, actual_volume_table],
        ):
            try:
                options[ens][source] = read_zone_options(table[ens], real)
            except KeyError:
                options[ens][source] = []
        options[ens][GraphSource.UNSMRY] = []
    return options


def process_files(
    cont_bound: Optional[str],
    haz_bound: Optional[str],
    well_file: Optional[str],
    root: str,
) -> List[Optional[str]]:
    """
    Checks if the files exist (otherwise gives a warning and returns None)
    Concatenates ensemble root dir and path to file if relative
    """
    return [
        _process_file(source, root) for source in [cont_bound, haz_bound, well_file]
    ]


def _process_file(file: Optional[str], root: str) -> Optional[str]:
    if file is not None:
        file = _check_if_file_exists(
            os.path.join(Path(root).parents[1], file)
            if not Path(file).is_absolute()
            else file
        )
    return file


def _check_if_file_exists(file: str) -> Optional[str]:
    if not os.path.isfile(file):
        warnings.warn(f"Cannot find specified file {file}.")
        return None
    return file
