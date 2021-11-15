from typing import List, Optional, Sequence

import pandas as pd

from webviz_subsurface_components import ExpressionInfo
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency

from .utils.from_timeseries_cumulatives import (
    calculate_from_resampled_cumulative_vectors_df,
    calculate_from_cumulative_vectors_with_resampling_df,
    get_cumulative_vector_name,
    is_interval_or_average_vector,
)

from ..._utils.vector_calculator import (
    get_selected_expressions,
)
from .utils.sampling_frequency_utils import frequency_leq

# TODO: Ensure good naming of class, suggestions listed:
# - VectorDataAccessor
# - AssembledVectorDataAccessor
# - AuthoredVectorDataAccessor
# - ConstructedVectorDataAccessor
# - ExtendedVectorDataAccessor
# - GeneratedVectorDataAccessor
# - ManufacturedVectorDataAccessor
# - ProducedVectorDataAccessor
# - Use "Provider" as ending instead? ...Provider
class AssembledVectorDataAccessor:
    """
    Class to create and provide access to data for a set of vector types, for a given
    ensemble summary provider.

    A sequence of vector names are provided, and data is fetched or created based on which
    type of vectors are present in the sequence.

    Vector names can be regular vectors existing among vector names in provider, Interval
    Delta/Average rate vector or a calculated vector from vector calculator.

    Based on the vector type, the class provides an interface for retrieveing dataframes
    for the set of such vectors for the provider.
    """

    def __init__(
        self,
        name: str,
        provider: EnsembleSummaryProvider,
        vector_names: Sequence[str],
        expressions: Optional[List[ExpressionInfo]] = None,
        resampling_frequency: Optional[Frequency] = None,
    ) -> None:
        self._name = name
        self._provider = provider
        self._provider_vectors = [
            vector for vector in vector_names if vector in provider.vector_names()
        ]
        self._interval_and_average_vectors = [
            elm
            for elm in vector_names
            if is_interval_or_average_vector(elm)
            and get_cumulative_vector_name(elm) in provider.vector_names()
        ]
        self._vector_calculator_expressions = (
            get_selected_expressions(expressions, vector_names)
            if expressions is not None
            else []
        )
        self._resampling_frequency = (
            resampling_frequency if self._provider.supports_resampling() else None
        )

    def has_provider_vectors(self) -> bool:
        return len(self._provider_vectors) > 0

    def has_interval_and_average_vectors(self) -> bool:
        return len(self._interval_and_average_vectors) > 0

    def has_vector_calculator_vectors(self) -> bool:
        return len(self._vector_calculator_expressions) > 0

    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        if not self.has_provider_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no provider vectors'
            )
        return self._provider.get_vectors_df(
            self._provider_vectors, self._resampling_frequency, realizations
        )

    def create_interval_and_average_vectors_df(
        self,
        calculation_sample_frequency: Frequency,  # TODO: use Optional[Frequency]?
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Get dataframe with interval delta and average rate vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding interval delta
        or average rate data

        `Input:`
        * calculation_sample_frequency: Frequency - Sampling frequency for inteval delta and average
        rate calculation
        * realizations: Sequence[int] - Sequency of realization numbers to include in calculation

        `Output:`
        * dataframe with interval  vector names in columns and their cumulative data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        ---------------------
        `TODO:`
        * Verify calculation of cumulative
        * IMPROVE FUNCTION NAME?
        """

        if self._provider.supports_resampling():
            return self.__create_interval_and_average_vectors_df_from_ondemand_resampling_provider(
                calculation_sample_frequency, realizations
            )

        return self.__create_interval_and_average_vectors_df_with_presampled_provider(
            calculation_sample_frequency, realizations
        )

    def __create_interval_and_average_vectors_df_with_presampled_provider(
        self,
        calculation_sample_frequency: Frequency,  # TODO: use Optional[Frequency]?
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Get dataframe with interval delta and average rate vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding interval delta
        or average rate data

        `Input:`
        * calculation_sample_frequency: Frequency - Sampling frequency for inteval delta and average
        rate calculation
        * realizations: Sequence[int] - Sequency of realization numbers to include in calculation

        `Output:`
        * dataframe with interval  vector names in columns and their cumulative data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        ---------------------
        `TODO:`
        * Verify calculation of cumulative
        * IMPROVE FUNCTION NAME!
        """
        if not self.has_interval_and_average_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no interval delta '
                "and average rate vector names"
            )

        cumulative_vector_names = [
            get_cumulative_vector_name(elm)
            for elm in self._interval_and_average_vectors
            if is_interval_or_average_vector(elm)
        ]
        cumulative_vector_names = list(sorted(set(cumulative_vector_names)))

        # TODO: Fetch vectors df with correct sampling and perform calculation.
        # Ensure valid sampling and ensure correct AVG_ calucaltion (unit/day)
        # calculation, i.e num days between sampling points
        vectors_df = self._provider.get_vectors_df(
            cumulative_vector_names, self._resampling_frequency, realizations
        )

        # Get the sampling frequency of dataframe
        vector_df_sampling_frequency: str = (
            str(self._resampling_frequency.value)
            if self._resampling_frequency is not None
            and self._resampling_frequency.value is not None
            else calculation_sample_frequency.value
        )

        # Requested sampling frequency of the calculation
        resampling_frequency_str = calculation_sample_frequency.value

        interval_and_average_vectors_df = pd.DataFrame()
        for vector_name in self._interval_and_average_vectors:
            cumulative_vector_name = get_cumulative_vector_name(vector_name)
            interval_and_average_vector_df = (
                calculate_from_cumulative_vectors_with_resampling_df(
                    vectors_df[["DATE", "REAL", cumulative_vector_name]],
                    sampling_frequency=vector_df_sampling_frequency,
                    resampling_frequency=resampling_frequency_str,
                    as_rate_per_day=vector_name.startswith("AVG_"),
                )
            )
            if interval_and_average_vectors_df.empty:
                interval_and_average_vectors_df = interval_and_average_vector_df
            else:
                interval_and_average_vectors_df = pd.merge(
                    interval_and_average_vectors_df,
                    interval_and_average_vector_df,
                    how="inner",
                )

        return interval_and_average_vectors_df

    def __create_interval_and_average_vectors_df_from_ondemand_resampling_provider(
        self,
        calculation_sample_frequency: Frequency,  # TODO: use Optional[Frequency]?
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Get dataframe with interval delta and average rate vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding interval delta
        or average rate data

        `Input:`
        * calculation_sample_frequency: Frequency - Sampling frequency for inteval delta and average
        rate calculation
        * realizations: Sequence[int] - Sequency of realization numbers to include in calculation

        `Output:`
        * dataframe with interval  vector names in columns and their cumulative data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        ---------------------
        `TODO:`
        * Verify calculation of cumulative
        * IMPROVE FUNCTION NAME!
        """
        if not self.has_interval_and_average_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no interval delta '
                "and average rate vector names"
            )

        def _verify_sampling_frequency_request(
            provider_resampling_frequency: Optional[Frequency],
            calculation_sample_frequency: Frequency,
        ) -> None:
            if provider_resampling_frequency is None:
                # TODO: How to handle resampling with None as freq?
                raise ValueError(
                    "Provider is configured with {None} as resampling frequency, raw data not handled yet!"
                )

            if not frequency_leq(
                provider_resampling_frequency, calculation_sample_frequency
            ):
                raise ValueError(
                    f"The requested resampling frequency {calculation_sample_frequency.value} "
                    "is higher than the resampling frequency for provider "
                    f"{provider_resampling_frequency.value}."
                )

        _verify_sampling_frequency_request(
            self._resampling_frequency, calculation_sample_frequency
        )

        cumulative_vector_names = [
            get_cumulative_vector_name(elm)
            for elm in self._interval_and_average_vectors
            if is_interval_or_average_vector(elm)
        ]
        cumulative_vector_names = list(sorted(set(cumulative_vector_names)))

        # TODO: Fetch vectors df with correct sampling and perform calculation.
        # Ensure valid sampling and ensure correct AVG_ calucaltion (unit/day)
        # calculation, i.e num days between sampling points
        vectors_df = self._provider.get_vectors_df(
            cumulative_vector_names, calculation_sample_frequency, realizations
        )

        interval_and_average_vectors_df = pd.DataFrame()
        for vector_name in self._interval_and_average_vectors:
            cumulative_vector_name = get_cumulative_vector_name(vector_name)
            interval_and_average_vector_df = (
                calculate_from_resampled_cumulative_vectors_df(
                    vectors_df[["DATE", "REAL", cumulative_vector_name]],
                    as_rate_per_day=vector_name.startswith("AVG_"),
                )
            )
            if interval_and_average_vectors_df.empty:
                interval_and_average_vectors_df = interval_and_average_vector_df
            else:
                interval_and_average_vectors_df = pd.merge(
                    interval_and_average_vectors_df,
                    interval_and_average_vector_df,
                    how="inner",
                )

        return interval_and_average_vectors_df

    def create_vector_calculator_vectors_df(self) -> pd.DataFrame:
        if not self.has_vector_calculator_vectors():
            raise ValueError(
                f'Assembled vector data accessor for provider "{self._name}"'
                "has no vector calculator expressions"
            )
        raise ValueError("Method not implemented!")
