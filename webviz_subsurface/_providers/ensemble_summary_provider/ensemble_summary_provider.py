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


class DateSpan(Enum):
    INTERSECTION = "intersection"
    UNION = "union"


@dataclass(frozen=True)
class ResamplingOptions:
    """Specifies resampling options, most notably the resampling frequency.
    Can also specify a `common_date_span` that will influence which dates get included
    in the returned time series data.
      * DateSpan.INTERSECTION - truncates the returned range of dates so that all returned
        realizations have the same date range. The returned range of dates will be
        the intersection of the date range available per requested realization.
      * DateSpan.UNION - extends the returned range of dates so that all realizations
        have same date range and the same dates. The returned range of dates will be the
        union of the date ranges available per requested realization. Vector values will
        be extrapolated.
      * None - each returned realization will contain dates according to the requested
        frequency, but no effort will be made to truncate or expand the total date range
        in order to align stert and end dates between realizations.
    """

    frequency: Frequency
    common_date_span: Optional[DateSpan] = None


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
        ...

    @abc.abstractmethod
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:
        """Returns list vector names with the option of excluding vectors that have only
        0-values and/or vectors where all the values are equal.
        """
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        """Returns list of all available realization numbers."""
        ...

    @abc.abstractmethod
    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        """Returns metadata for the specified vector. Returns None if no metadata
        exists or if any of the non-optional properties of `VectorMetadata` are missing.
        """
        ...

    @abc.abstractmethod
    def supports_resampling(self) -> bool:
        """Returns True if this provider supports resampling, otherwise False.
        A provider that doesn't support resampling will only accept None as value for
        the resampling_frequency parameter in `dates()` and the `resampling_options` in
        `get_vectors_df()`.
        """
        ...

    @abc.abstractmethod
    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        date_span: DateSpan = DateSpan.UNION,
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:
        """Returns the intersection or union of available dates for the specified
        realizations depending on the specified value `date_span`.
        """
        ...

    @abc.abstractmethod
    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_options: Optional[ResamplingOptions],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Returns a Pandas DataFrame with data for the vectors specified in `vector_names.`

        For a provider that supports resampling, the `resampling_options` parameter
        object controls the sampling frequency of the returned data and the number of
        dates to return for each realization.
        If `resampling_options` is None, the data will be returned with full/raw resolution.
        For a provider that does not support resampling, the `resampling_options` parameter
        must always be None, otherwise an exception will be raised.

        The returned DataFrame will always contain a 'DATE' and 'REAL' column in addition
        to columns for all the requested vectors.
        """
        ...

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
        ...
