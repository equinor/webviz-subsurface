from pathlib import Path
from typing import Dict

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from .ensemble_summary_provider_set import EnsembleSummaryProviderSet


def create_lazy_ensemble_summary_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
    rel_file_pattern: str,
) -> EnsembleSummaryProviderSet:
    """Create set of ensemble summary providers with lazy (on-demand) resampling/interpolation,
    from dictionary of ensemble name and corresponding arrow file paths

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value
    * rel_file_pattern: str - specify a relative (per realization) file pattern to find the
    wanted .arrow files within each realization

    `Return:`
    Provider set with ensemble summary providers with lazy (on-demand) resampling/interpolation
    """
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_lazy(
            str(path), rel_file_pattern
        )
    return EnsembleSummaryProviderSet(provider_dict)


def create_presampled_ensemble_summary_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
    rel_file_pattern: str,
    presampling_frequency: Frequency,
) -> EnsembleSummaryProviderSet:
    """Create set of ensemble summary providers without lazy resampling, but with specified
    frequency, from dictionary of ensemble name and corresponding arrow file paths

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value
    * rel_file_pattern: str - specify a relative (per realization) file pattern to find the
    wanted .arrow files within each realization
    * presampling_frequency: Frequency - Frequency to sample input data in factory with, during
    import.

    `Return:`
    Provider set with ensemble summary providers with presampled data according to specified
    presampling frequency.
    """
    # TODO: Make presampling_frequency: Optional[Frequency] when allowing raw data for plugin
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_presampled(
            str(path), rel_file_pattern, presampling_frequency
        )
    return EnsembleSummaryProviderSet(provider_dict)
