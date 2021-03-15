import abc
from typing import List, Dict, Optional, Sequence

import pandas as pd
import numpy as np


# fmt: off

#class LabeledColumnData:
#    column_name: str
#    realization: int
#    values: np.ndarray
#
#class NamedColumnData:
#    column_name: str
#    realization_list: List[int]
#    values_list: List[np.ndarray]
#
#    @staticmethod
#    def to_dataframe(column_data_list: List["NamedColumnData"]) -> pd.DataFrame: ...


class EnsembleTableModel(abc.ABC):
    @abc.abstractmethod
    def column_names(self) -> List[str]: ...

    # def has_column(column_name:str) -> bool: ...
    # def has_columns(column_names: List[str]) -> bool: ...

    @abc.abstractmethod
    def realizations(self) -> List[int]: ...

    @abc.abstractmethod
    def get_column_values_numpy(self, column_name: str, realizations: Optional[Sequence[int]] = None) -> List[np.ndarray]:   ...

    @abc.abstractmethod
    def get_column_values_df(self, column_name: str, realizations: Optional[Sequence[int]] = None) -> pd.DataFrame:   ...

    @abc.abstractmethod
    def get_columns_values_df(self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> pd.DataFrame:   ...

    # def get_columns_values(self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> List[LabeledColumnData]:   ...
    # def get_columns_values(self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> List[NamedColumnData]:   ...

    # def get_realizations_based_on_filter(self, filter_column_name: str, column_values: list) -> Sequence[int]: ...

# fmt: on


class EnsembleTableModelSet:
    def __init__(self, table_models: Dict[str, EnsembleTableModel]) -> None:
        self._table_models = table_models

    def ensemble_names(self) -> List[str]:
        return list(self._table_models.keys())

    def ensemble(self, ensemble_name: str) -> EnsembleTableModel:
        return self._table_models[ensemble_name]
