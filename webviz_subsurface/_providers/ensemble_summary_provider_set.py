from typing import List, Dict

from .ensemble_summary_provider import EnsembleSummaryProvider


class EnsembleSummaryProviderSet:
    def __init__(self, provider_dict: Dict[str, EnsembleSummaryProvider]) -> None:
        self._provider_dict = provider_dict.copy()

    def ensemble_names(self) -> List[str]:
        return list(self._provider_dict.keys())

    def provider(self, ensemble_name: str) -> EnsembleSummaryProvider:
        return self._provider_dict[ensemble_name]

    def all_providers(self) -> List[EnsembleSummaryProvider]:
        return list(self._provider_dict.values())
