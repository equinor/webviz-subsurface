from typing import List, Optional, Sequence
import datetime
import abc

import pandas as pd


# Class provides data for ensemble summary (timeseries)
class EnsembleSummaryProvider(abc.ABC):
    @abc.abstractmethod
    def vector_names(self) -> List[str]:
        ...

    @abc.abstractmethod
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        ...

    @abc.abstractmethod
    def dates(
        self, realizations: Optional[Sequence[int]] = None
    ) -> List[datetime.datetime]:
        ...

    @abc.abstractmethod
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        ...
