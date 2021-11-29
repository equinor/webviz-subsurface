from typing import Dict, ItemsView, List, Optional
from pathlib import Path

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
    VectorMetadata,
)

# TODO: Consider if "ensemble" should be a part of names in class (Both class name,
# function names and attribute names).
class ProviderSet:
    """
    Class to create a set of ensemble summary providers with unique names

    Provides interface for read-only fetching of provider data
    """

    def __init__(self, provider_dict: Dict[str, EnsembleSummaryProvider]) -> None:
        self._provider_dict = provider_dict.copy()
        self._all_vector_names = self._create_union_of_vector_names_from_providers(
            list(self._provider_dict.values())
        )

    def verify_consistent_vector_metadata(self) -> None:
        """
        Verify that vector metadata is consistent across providers, raise exception
        if inconsistency occur.

        TODO:
        * Improve print of inconsistent metadata info - store all inconsistencies
        and print, do not raise ValueError on first.
        * Replace with vector metadata dataclass object when updated (__eq__ operator
        for dataclass would be handy)
        """

        # Iterate through all vector names for provider set
        for vector_name in self._all_vector_names:
            # Store provider name and retrieved vector metadata for specific vector name
            vector_provider_metadata_dict: Dict[str, Optional[VectorMetadata]] = {}

            # Retrieve vector metadata from providers
            for name, provider in self._provider_dict.items():
                if vector_name in provider.vector_names():
                    vector_provider_metadata_dict[name] = provider.vector_metadata(
                        vector_name
                    )
            if vector_provider_metadata_dict:
                validator_provider, metadata_validator = list(
                    vector_provider_metadata_dict.items()
                )[0]
                for (
                    provider_name,
                    vector_metadata,
                ) in vector_provider_metadata_dict.items():
                    if vector_metadata != metadata_validator:

                        raise ValueError(
                            f'Inconsistent vector metadata for vector "{vector_name}"'
                            f' between provider "{validator_provider}" and provider '
                            f'{provider_name}"'
                        )

    @staticmethod
    def _create_union_of_vector_names_from_providers(
        providers: List[EnsembleSummaryProvider],
    ) -> List[str]:
        """Create list with the union of vector names among providers"""
        vector_names = []
        for provider in providers:
            vector_names.extend(provider.vector_names())
        vector_names = list(sorted(set(vector_names)))
        return vector_names

    def items(self) -> ItemsView[str, EnsembleSummaryProvider]:
        return self._provider_dict.items()

    def names(self) -> List[str]:
        return list(self._provider_dict.keys())

    def provider(self, name: str) -> EnsembleSummaryProvider:
        if name not in self._provider_dict.keys():
            raise ValueError(f'Provider with name "{name}" not present in set!')
        return self._provider_dict[name]

    def all_providers(self) -> List[EnsembleSummaryProvider]:
        return list(self._provider_dict.values())

    def all_vector_names(self) -> List[str]:
        """Create list with the union of vector names among providers"""
        return self._all_vector_names

    def vector_metadata(self, vector: str) -> Optional[VectorMetadata]:
        """Get vector metadata from first occurrence among providers,

        `return:`
        Vector metadata from first occurrence among providers, None if not existing
        """
        metadata: Optional[VectorMetadata] = next(
            (
                provider.vector_metadata(vector)
                for provider in self._provider_dict.values()
                if vector in provider.vector_names()
                and provider.vector_metadata(vector)
            ),
            None,
        )
        return metadata


def create_lazy_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
) -> ProviderSet:
    """Create set of providers with lazy (on-demand) resampling/interpolation, from
    dictionary of ensemble name and corresponding arrow file paths

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value

    `Return:`
    Provider set with ensemble summary providers with lazy (on-demand) resampling/interpolation
    """
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_lazy(str(path))
    return ProviderSet(provider_dict)


def create_presampled_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
    presampling_frequency: Frequency,
) -> ProviderSet:
    """Create set of providers without lazy resampling, but with specified frequency, from
    dictionary of ensemble name and corresponding arrow file paths

    `Input:`
    * name_path_dict: Dict[str, Path] - ensemble name as key and arrow file path as value
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
            str(path), presampling_frequency
        )
    return ProviderSet(provider_dict)
