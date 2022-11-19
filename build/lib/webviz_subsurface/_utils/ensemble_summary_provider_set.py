import datetime
from typing import Dict, ItemsView, List, Optional, Sequence, Set

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    Frequency,
    VectorMetadata,
)


class EnsembleSummaryProviderSet:
    """
    Class to create a set of ensemble summary providers with unique names

    Provides interface for read-only fetching of provider data

    NOTE:
        - Assuming same implementation of EnsembleSummaryProvider interface across
        all providers in set. There is no guarantee of functionality if various
        provider implementations are mixed in the same set.
    """

    def __init__(self, provider_dict: Dict[str, EnsembleSummaryProvider]) -> None:
        self._provider_dict = provider_dict.copy()
        self._names = list(self._provider_dict.keys())
        self._all_vector_names = self._create_union_of_vector_names_from_providers(
            list(self._provider_dict.values())
        )
        self._all_realizations = self._create_union_of_realizations_from_providers(
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

    @staticmethod
    def _create_union_of_realizations_from_providers(
        providers: Sequence[EnsembleSummaryProvider],
    ) -> List[int]:
        """Create list with the union of realizations among providers"""
        realizations: Set[int] = set()
        for provider in providers:
            realizations.update(provider.realizations())
        output = list(sorted(realizations))
        return output

    def items(self) -> ItemsView[str, EnsembleSummaryProvider]:
        return self._provider_dict.items()

    def provider_names(self) -> List[str]:
        return self._names

    def provider(self, name: str) -> EnsembleSummaryProvider:
        if name not in self._provider_dict.keys():
            raise ValueError(f'Provider with name "{name}" not present in set!')
        return self._provider_dict[name]

    def all_providers(self) -> List[EnsembleSummaryProvider]:
        return list(self._provider_dict.values())

    def all_dates(
        self,
        resampling_frequency: Optional[Frequency],
    ) -> List[datetime.datetime]:
        """List with the union of dates among providers"""
        dates_union: Set[datetime.datetime] = set()
        for provider in self.all_providers():
            _dates = set(provider.dates(resampling_frequency, None))
            dates_union.update(_dates)
        return list(sorted(dates_union))

    def all_realizations(self) -> List[int]:
        """List with the union of realizations among providers"""
        return self._all_realizations

    def all_vector_names(self) -> List[str]:
        """List with the union of vector names among providers"""
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
