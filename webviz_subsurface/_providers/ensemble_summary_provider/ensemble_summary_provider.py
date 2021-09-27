from typing import List, Optional, Sequence, Dict, Any
import datetime
import abc
from enum import Enum

import pandas as pd


class Frequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

    @classmethod
    def from_string_value(cls, value: str) -> Optional["Frequency"]:
        try:
            return cls(value)
        except ValueError:
            return None


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
    def vector_metadata(self, vector_name: str) -> Optional[Dict[str, Any]]:
        ...

    @abc.abstractmethod
    def supports_resampling(self) -> bool:
        ...

    @abc.abstractmethod
    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:
        """Returns the intersection of available dates.
        Note that when resampling_frequency is None, the pure intersection of the
        stored raw dates will be returned. Thus the returned list of dates will not include
        dates from long running realizations.
        For other resampling frequencies, the date range will be expanded to cover the entire
        time range of all the requested realizations before computing the resampled dates.
        """
        ...

    @abc.abstractmethod
    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
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
