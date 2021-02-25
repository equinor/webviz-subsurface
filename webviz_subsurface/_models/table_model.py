import abc
from typing import List, Dict, Optional, Sequence
from pathlib import Path

import pandas as pd
import numpy as np


# fmt: off

class EnsembleTableModel(abc.ABC):
    @abc.abstractmethod
    def column_names(self) -> List[str]: ...

    # def has_column(column_name:str) -> bool: ...
    # def has_columns(column_names: List[str]) -> bool: ...

    @abc.abstractmethod 
    def realizations(self) -> List[int]: ...

    @abc.abstractmethod
    def get_column_values_numpy(self, column_name: str, realizations: Optional[Sequence[int]] = None) -> List[np.ndarray]:   ...
    def get_column_values_df(self, column_name: str, realizations: Optional[Sequence[int]] = None) -> pd.DataFrame:   ...

    # def get_realizations_based_on_filter(self, filter_column_name: str, column_values: list) -> Sequence[int]: ...


# fmt: on


class EnsembleTableModelSet:
    def __init__(self, table_models: Dict[str, EnsembleTableModel]) -> None:
        self._table_models = table_models

    def ensemble_names(self) -> List[str]:
        return list(self._table_models.keys())

    def ensemble(self, ensemble_name: str) -> EnsembleTableModel:
        return self._table_models[ensemble_name]

    # Tja...
    # def selector_columns(self) -> List:
    # def filter_columns(self) -> List:
