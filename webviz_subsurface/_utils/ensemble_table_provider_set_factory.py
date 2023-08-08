from pathlib import Path
from typing import Dict

from webviz_subsurface._providers import (
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
)

from .ensemble_table_provider_set import EnsembleTableProviderSet


def create_csvfile_providerset_from_paths(
    name_path_dict: Dict[str, Path],
    rel_file_pattern: str,
) -> EnsembleTableProviderSet:
    """Create set of ensemble summary providers without lazy resampling, but with specified
    frequency, from dictionary of ensemble name and corresponding arrow file paths

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value
    * rel_file_pattern: str - specify a relative (per realization) file pattern to find the
    wanted .csv files within each realization

    `Return:`
    Provider set with ensemble summary providers with presampled data according to specified
    presampling frequency.
    """
    # TODO: Make presampling_frequency: Optional[Frequency] when allowing raw data for plugin
    provider_factory = EnsembleTableProviderFactory.instance()
    provider_dict: Dict[str, EnsembleTableProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_per_realization_csv_file(
            str(path), rel_file_pattern
        )
    return EnsembleTableProviderSet(provider_dict)


def create_parameter_providerset_from_paths(
    name_path_dict: Dict[str, Path]
) -> EnsembleTableProviderSet:
    """Create set of ensemble table providers

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value
    * rel_file_pattern: str - specify a relative (per realization) file pattern to find the
    wanted .csv files within each realization

    `Return:`
    Provider set with ensemble summary providers with presampled data according to specified
    presampling frequency.
    """
    # TODO: Make presampling_frequency: Optional[Frequency] when allowing raw data for plugin
    provider_factory = EnsembleTableProviderFactory.instance()
    provider_dict: Dict[str, EnsembleTableProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[
            name
        ] = provider_factory.create_from_per_realization_parameter_file(str(path))
    return EnsembleTableProviderSet(provider_dict)
