from typing import Dict, List, Optional
from pathlib import Path

from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleSummaryProvider,
    Frequency,
)

# TODO: This class resembles EnsembleSetModel in webviz_subsurface/_models/ensemble_set_model.py
# with usage of EnsembleSummaryProvider instead of EnsembleModel?
class EnsembleSetModel:
    """
    Class to create a set of ensemble summary providers with names from given paths.

    Provides interface for read-only fetching of data
    """

    def __init__(
        self,
        ensemble_paths: Dict[str, Path],
        sampling: str,
    ) -> None:
        self._ensemble_provider_set: Dict[
            str, EnsembleSummaryProvider
        ] = self.__create_provider_set_from_paths(ensemble_paths)
        self._resampling_frequency = Frequency.from_string_value(sampling)
        self._vector_names: List[str] = self.__create_vector_names_list_from_providers(
            list(self._ensemble_provider_set.values())
        )

    def ensemble_names(self) -> List[str]:
        return list(self._ensemble_provider_set.keys())

    def ensemble_provider_set(self) -> Dict[str, EnsembleSummaryProvider]:
        return self._ensemble_provider_set

    def ensemble_provider(self, ensemble_name: str) -> EnsembleSummaryProvider:
        if ensemble_name not in self._ensemble_provider_set.keys():
            raise ValueError(
                f'Ensemble "{ensemble_name}" not present in provider set for model!'
            )
        return self._ensemble_provider_set[ensemble_name]

    def resampling_frequency(self) -> Optional[Frequency]:
        return self._resampling_frequency

    def vector_names(self) -> List[str]:
        return self._vector_names

    @staticmethod
    def __create_provider_set_from_paths(
        ensemble_paths: Dict[str, Path],
    ) -> Dict[str, EnsembleSummaryProvider]:
        provider_factory = EnsembleSummaryProviderFactory.instance()
        provider_set: Dict[str, EnsembleSummaryProvider] = {}
        for ensemble_name, ensemble_path in ensemble_paths.items():
            provider_set[
                ensemble_name
            ] = provider_factory.create_from_arrow_unsmry_lazy(str(ensemble_path))
        return provider_set

    @staticmethod
    def __create_vector_names_list_from_providers(
        ensemble_providers: List[EnsembleSummaryProvider],
    ) -> List[str]:
        """Create list with the union of vector names among providers"""
        vector_names = []
        for provider in ensemble_providers:
            vector_names.extend(provider.vector_names())
        vector_names = list(sorted(set(vector_names)))
        return vector_names
