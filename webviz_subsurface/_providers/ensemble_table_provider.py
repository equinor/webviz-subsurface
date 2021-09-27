import abc
from typing import Dict, List, Optional, Sequence

import pandas as pd


class EnsembleTableProvider(abc.ABC):
    @abc.abstractmethod
    def column_names(self) -> List[str]:
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        ...

    @abc.abstractmethod
    def get_column_data(
        self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...


class EnsembleTableProviderSet:
    def __init__(self, provider_dict: Dict[str, EnsembleTableProvider]) -> None:
        self._provider_dict = provider_dict

    def ensemble_names(self) -> List[str]:
        return list(self._provider_dict.keys())

    def ensemble_provider(self, ensemble_name: str) -> EnsembleTableProvider:
        return self._provider_dict[ensemble_name]
