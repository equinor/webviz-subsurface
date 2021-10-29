import abc
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

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


@dataclass(frozen=True)
class VectorMetadata:
    unit: str
    is_total: bool
    is_rate: bool
    is_historical: bool
    keyword: str
    wgname: Optional[str]
    get_num: Optional[int]


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
    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        """Returns metadata for the specified vector. Returns None if no metadata
        exists or if any of the non-optional properties of VectorMetadata are missing.
        """
        ...

    @abc.abstractmethod
    def supports_resampling(self) -> bool:
        """Returns True if this provider supports resampling, otherwise False.
        A provider that doesn't support resampling will only accept None as value for
        the resampling_frequency parameter in dates() and get_vectors_df().
        """
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
