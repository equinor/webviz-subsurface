import logging
import os
import warnings
from pathlib import Path
from typing import Dict, List, Optional

from fmu.ensemble import ScratchEnsemble
from webviz_config import WebvizSettings

from webviz_subsurface._providers import (
    EnsembleSurfaceProvider,
    EnsembleSurfaceProviderFactory,
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)
from webviz_subsurface._providers.ensemble_polygon_provider import PolygonServer
from webviz_subsurface._providers.ensemble_surface_provider._surface_discovery import (
    discover_per_realization_surface_files,
)
from webviz_subsurface.plugins._co2_leakage._utilities.containment_data_provider import (
    ContainmentDataProvider,
)
from webviz_subsurface.plugins._co2_leakage._utilities.ensemble_well_picks import (
    EnsembleWellPicks,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    BoundarySettings,
    FilteredMapAttribute,
    GraphSource,
    MapAttribute,
    MapNamingConvention,
    MenuOptions,
)
from webviz_subsurface.plugins._co2_leakage._utilities.polygon_handler import (
    PolygonHandler,
)
from webviz_subsurface.plugins._co2_leakage._utilities.unsmry_data_provider import (
    UnsmryDataProvider,
)

LOGGER = logging.getLogger(__name__)
LOGGER_TO_SUPPRESS = logging.getLogger(
    "webviz_subsurface._providers.ensemble_summary_provider._arrow_unsmry_import"
)
LOGGER_TO_SUPPRESS.setLevel(logging.ERROR)  # We replace the given warning with our own
WARNING_THRESHOLD_CSV_FILE_SIZE_MB = 100.0


def build_mapping(
    webviz_settings: WebvizSettings,
    ensembles: List[str],
) -> Dict[str, str]:
    available_attrs_per_ensemble = [
        discover_per_realization_surface_files(
            webviz_settings.shared_settings["scratch_ensembles"][ens],
            "share/results/maps",
        )
        for ens in ensembles
    ]
    full_attr_list = [
        [attr.attribute for attr in ens] for ens in available_attrs_per_ensemble
    ]
    unique_attributes = set()
    for ens_attr in full_attr_list:
        unique_attributes.update(ens_attr)
    unique_attributes_list = list(unique_attributes)
    mapping = {}
    for attr in unique_attributes_list:
        for name_convention in MapNamingConvention:
            if attr == name_convention.value:
                attribute_key = MapAttribute[name_convention.name].name
                mapping[attribute_key] = attr
                break
    return mapping


def init_map_attribute_names(
    webviz_settings: WebvizSettings,
    ensembles: List[str],
    input_mapping: Optional[Dict[str, str]],
) -> FilteredMapAttribute:
    default_mapping = build_mapping(webviz_settings, ensembles)
    final_mapping = dict(default_mapping)
    if input_mapping is not None:
        for key, value in input_mapping.items():
            if key in final_mapping and final_mapping[key] != value:
                LOGGER.info(
                    f"Conflict on attribute '{key}': prioritizing '{value}' (from input attributes)"
                    f" over '{final_mapping[key]}' (from default attributes)"
                )
            final_mapping[key] = value
    final_attributes = {
        (MapAttribute[key].value if key in MapAttribute.__members__ else key): value
        for key, value in final_mapping.items()
    }
    return FilteredMapAttribute(final_attributes)


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
    ensemble_paths: Dict[str, str],
    well_pick_path: Optional[str],
    map_surface_names_to_well_pick_names: Optional[Dict[str, str]],
) -> Dict[str, EnsembleWellPicks]:
    if well_pick_path is None:
        return {}

    return {
        ens: EnsembleWellPicks(
            ens_p, well_pick_path, map_surface_names_to_well_pick_names
        )
        for ens, ens_p in ensemble_paths.items()
    }


def init_polygon_provider_handlers(
    server: PolygonServer,
    ensemble_paths: Dict[str, str],
    options: Optional[BoundarySettings],
) -> Dict[str, PolygonHandler]:
    filled_options: BoundarySettings = {
        "polygon_file_pattern": "share/results/polygons/*.csv",
        "attribute": "boundary",
        "hazardous_name": "hazardous",
        "containment_name": "containment",
    }
    if options is not None:
        filled_options.update(options)
    return {
        ens: PolygonHandler(
            server,
            ens_path,
            filled_options,
        )
        for ens, ens_path in ensemble_paths.items()
    }


def init_unsmry_data_providers(
    ensemble_roots: Dict[str, str],
    table_rel_path: Optional[str],
) -> Dict[str, UnsmryDataProvider]:
    if table_rel_path is None:
        return {}
    factory = EnsembleTableProviderFactory.instance()
    providers = {
        ens: _init_ensemble_table_provider(factory, ens, ens_path, table_rel_path)
        for ens, ens_path in ensemble_roots.items()
    }
    return {k: UnsmryDataProvider(v) for k, v in providers.items() if v is not None}


def init_containment_data_providers(
    ensemble_roots: Dict[str, str],
    table_rel_path: Optional[str],
) -> Dict[str, ContainmentDataProvider]:
    if table_rel_path is None:
        return {}
    factory = EnsembleTableProviderFactory.instance()
    providers = {
        ens: _init_ensemble_table_provider(factory, ens, ens_path, table_rel_path)
        for ens, ens_path in ensemble_roots.items()
    }
    return {
        k: ContainmentDataProvider(v) for k, v in providers.items() if v is not None
    }


def _init_ensemble_table_provider(
    factory: EnsembleTableProviderFactory,
    ens: str,
    ens_path: str,
    table_rel_path: str,
) -> Optional[EnsembleTableProvider]:
    try:
        return factory.create_from_per_realization_arrow_file(ens_path, table_rel_path)
    except (KeyError, ValueError) as exc:
        try:
            return factory.create_from_per_realization_csv_file(
                ens_path, table_rel_path
            )
        except (KeyError, ValueError) as exc2:
            LOGGER.warning(
                f'\nTried reading "{table_rel_path}" for ensemble "{ens}" as csv with'
                f" error \n- {exc2}, \nand as arrow with error \n- {exc}"
            )
    return None


def init_realizations(ensemble_paths: Dict[str, str]) -> Dict[str, List[int]]:
    realization_per_ens = {}
    for ens, ens_path in ensemble_paths.items():
        scratch_ensemble = ScratchEnsemble("dummyEnsembleName", paths=ens_path).filter(
            "OK"
        )
        realization_per_ens[ens] = sorted(list(scratch_ensemble.realizations.keys()))
    return realization_per_ens


def init_menu_options(
    ensemble_roots: Dict[str, str],
    mass_table: Dict[str, ContainmentDataProvider],
    actual_volume_table: Dict[str, ContainmentDataProvider],
    unsmry_providers: Dict[str, UnsmryDataProvider],
) -> Dict[str, Dict[GraphSource, MenuOptions]]:
    options: Dict[str, Dict[GraphSource, MenuOptions]] = {}
    for ens in ensemble_roots.keys():
        options[ens] = {}
        if ens in mass_table:
            options[ens][GraphSource.CONTAINMENT_MASS] = mass_table[ens].menu_options
        if ens in actual_volume_table:
            options[ens][GraphSource.CONTAINMENT_ACTUAL_VOLUME] = actual_volume_table[
                ens
            ].menu_options
        if ens in unsmry_providers:
            options[ens][GraphSource.UNSMRY] = unsmry_providers[ens].menu_options
    return options


def init_dictionary_of_content(
    menu_options: Dict[str, Dict[GraphSource, MenuOptions]],
    has_maps: bool,
) -> Dict[str, bool]:
    options = next(iter(menu_options.values()))
    content = {
        "mass": GraphSource.CONTAINMENT_MASS in options,
        "volume": GraphSource.CONTAINMENT_ACTUAL_VOLUME in options,
        "unsmry": GraphSource.UNSMRY in options,
    }
    content["any_table"] = max(content.values())
    content["maps"] = has_maps
    content["zones"] = False
    content["regions"] = False
    content["plume_groups"] = False
    if content["mass"] or content["volume"]:
        content["zones"] = max(
            len(inner_dict["zones"]) > 0
            for outer_dict in menu_options.values()
            for inner_dict in outer_dict.values()
        )
        content["regions"] = max(
            len(inner_dict["regions"]) > 0
            for outer_dict in menu_options.values()
            for inner_dict in outer_dict.values()
        )
        content["plume_groups"] = max(
            len(inner_dict["plume_groups"]) > 0
            for outer_dict in menu_options.values()
            for inner_dict in outer_dict.values()
        )
    return content


def _process_file(file: Optional[str], ensemble_path: str) -> Optional[str]:
    if file is not None:
        if Path(file).is_absolute():
            if os.path.isfile(Path(file)):
                return file
            warnings.warn(f"Cannot find specified file {file}.")
            return None
        file = os.path.join(Path(ensemble_path).parents[1], file)
        if not os.path.isfile(file):
            warnings.warn(
                f"Cannot find specified file {file}.\n"
                "Note that relative paths are accepted from ensemble root "
                "(directory with the realizations)."
            )
            return None
    return file
