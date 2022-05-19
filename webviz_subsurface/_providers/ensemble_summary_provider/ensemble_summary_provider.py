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
    QUARTERLY = "quarterly"
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
        """Returns list of all available vector names."""

    @abc.abstractmethod
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:
        """Returns list vector names with the option of excluding vectors that have only
        0-values and/or vectors where all the values are equal.
        """

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realization numbers."""

    @abc.abstractmethod
    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        """Returns metadata for the specified vector. Returns None if no metadata
        exists or if any of the non-optional properties of `VectorMetadata` are missing.
        """

    @abc.abstractmethod
    def supports_resampling(self) -> bool:
        """Returns True if this provider supports resampling, otherwise False.
        A provider that doesn't support resampling will only accept None as value for
        the resampling_frequency parameter in `dates()` and `get_vectors_df()`.
        """

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

    @abc.abstractmethod
    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Returns a Pandas DataFrame with data for the vectors specified in `vector_names.`

        For a provider that supports resampling, the `resampling_frequency` parameter
        controls the sampling frequency of the returned data. If `resampling_frequency` is
        None, the data will be returned with full/raw resolution.
        For a provider that does not support resampling, the `resampling_frequency` parameter
        must always be None, otherwise an exception will be raised.

        The returned DataFrame will always contain a 'DATE' and 'REAL' column in addition
        to columns for all the requested vectors.
        """

    @abc.abstractmethod
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Returns a Pandas DataFrame with data for the specified `date` and the vectors
        specified in `vector_names.`

        For a provider that supports resampling, all vectors will be resampled at the
        specified `date.` For providers that do not support resampling, an exact match on
        `date` will be required.

        The returned DataFrame will always contain a 'REAL' column in addition to
        columns for all the requested vectors.
        """
