from pathlib import Path
from typing import Any, Dict, ItemsView, List, Optional

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
)


# TODO: Consider if "ensemble" should be a part of names in class. Both class name,
# funciton names and attribute names
class ProviderSet:
    """
    Class to create a set of ensemble summary providers with unique names

    Provides interface for read-only fetching of provider data
    """

    def __init__(self, provider_dict: Dict[str, EnsembleSummaryProvider]) -> None:
        self._provider_dict = provider_dict.copy()
        self._all_vector_names: List[
            str
        ] = self._create_union_of_vector_names_from_providers(
            list(self._provider_dict.values())
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

    def vector_metadata(self, vector: str) -> Optional[Dict[str, Any]]:
        """Get vector metadata from first occurence among providers,

        `return:`
        Vector metadata dict from first occurence among providers, None if not existing
        """
        metadata: Optional[Dict[str, Any]] = next(
            (
                provider.vector_metadata(vector)
                for provider in self._provider_dict.values()
                if vector in provider.vector_names()
                and provider.vector_metadata(vector)
            ),
            None,
        )
        return metadata


def create_provider_set_from_paths(
    name_path_dict: Dict[str, Path],
) -> ProviderSet:
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for name, path in name_path_dict.items():
        provider_dict[name] = provider_factory.create_from_arrow_unsmry_lazy(str(path))
    return ProviderSet(provider_dict)
