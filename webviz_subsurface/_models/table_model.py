import abc
from typing import List, Dict, Optional, Sequence

import pandas as pd


# fmt: off

class EnsembleTableModel(abc.ABC):
    @abc.abstractmethod
    def column_names(self) -> List[str]: ...

    @abc.abstractmethod
    def realizations(self) -> List[int]: ...

    @abc.abstractmethod
    def get_column_data(self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> pd.DataFrame: ...

# fmt: on


class EnsembleTableModelSet:
    def __init__(self, table_models: Dict[str, EnsembleTableModel]) -> None:
        self._table_models = table_models

    def ensemble_names(self) -> List[str]:
        return list(self._table_models.keys())

    def ensemble(self, ensemble_name: str) -> EnsembleTableModel:
        return self._table_models[ensemble_name]
