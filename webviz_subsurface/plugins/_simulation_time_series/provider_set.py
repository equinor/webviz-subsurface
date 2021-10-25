from pathlib import Path
from typing import Any, Dict, List, Optional

from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
)


class ProviderSet:
    """
    Class to create a set of ensemble summary providers with names

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
        ensemble_providers: List[EnsembleSummaryProvider],
    ) -> List[str]:
        """Create list with the union of vector names among providers"""
        vector_names = []
        for provider in ensemble_providers:
            vector_names.extend(provider.vector_names())
        vector_names = list(sorted(set(vector_names)))
        return vector_names

    def ensemble_names(self) -> List[str]:
        return list(self._provider_dict.keys())

    def provider(self, ensemble_name: str) -> EnsembleSummaryProvider:
        if ensemble_name not in self._provider_dict.keys():
            raise ValueError(f'Ensemble "{ensemble_name}" not present in provider set!')
        return self._provider_dict[ensemble_name]

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
    ensemble_paths: Dict[str, Path],
) -> ProviderSet:
    provider_factory = EnsembleSummaryProviderFactory.instance()
    provider_dict: Dict[str, EnsembleSummaryProvider] = {}
    for ensemble_name, ensemble_path in ensemble_paths.items():
        provider_dict[ensemble_name] = provider_factory.create_from_arrow_unsmry_lazy(
            str(ensemble_path)
        )
    return ProviderSet(provider_dict)
