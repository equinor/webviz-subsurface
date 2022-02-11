import datetime
from typing import List, Optional, Sequence

import pandas as pd
from webviz_subsurface_components import ExpressionInfo

from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from webviz_subsurface._utils.vector_calculator import (
    create_calculated_vector_df,
    get_selected_expressions,
)

from ..utils import dataframe_utils
from ..utils.from_timeseries_cumulatives import (
    calculate_from_resampled_cumulative_vectors_df,
    get_cumulative_vector_name,
    is_per_interval_or_per_day_vector,
)
from .derived_vectors_accessor import DerivedVectorsAccessor


class DerivedEnsembleVectorsAccessorImpl(DerivedVectorsAccessor):
    """
    Class to create derived vector data and access these for a regular ensemble.

    The ensemble is represented with an ensemble summary provider.

    A list of vector names are provided, and data is fetched or created based on which
    type of vectors are present in the list.

    Vector names can be regular vectors existing among vector names in the provider, Per
    Interval/Per Day vector or a calculated vector from vector calculator.

    Based on the vector type, the class provides an interface for retrieveing dataframes
    for the set of such vectors for the provider.
    """

    def __init__(
        self,
        name: str,
        provider: EnsembleSummaryProvider,
        vectors: List[str],
        expressions: Optional[List[ExpressionInfo]] = None,
        resampling_frequency: Optional[Frequency] = None,
        relative_date: Optional[datetime.datetime] = None,
    ) -> None:
        # Initialize base class
        super().__init__(provider.realizations())

        self._name = name
        self._provider = provider
        self._provider_vectors = [
            vector for vector in vectors if vector in self._provider.vector_names()
        ]
        self._per_interval_and_per_day_vectors = [
            vector
            for vector in vectors
            if is_per_interval_or_per_day_vector(vector)
            and get_cumulative_vector_name(vector) in provider.vector_names()
        ]
        self._vector_calculator_expressions = (
            get_selected_expressions(expressions, vectors)
            if expressions is not None
            else []
        )
        self._resampling_frequency = (
            resampling_frequency if self._provider.supports_resampling() else None
        )
        self._relative_date = relative_date

    def has_provider_vectors(self) -> bool:
        return len(self._provider_vectors) > 0

    def has_per_interval_and_per_day_vectors(self) -> bool:
        return len(self._per_interval_and_per_day_vectors) > 0

    def has_vector_calculator_expressions(self) -> bool:
        return len(self._vector_calculator_expressions) > 0

    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        """Get dataframe for the selected provider vectors"""
        if not self.has_provider_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no provider vectors'
            )

        if self._relative_date:
            return dataframe_utils.create_relative_to_date_df(
                self._provider.get_vectors_df(
                    self._provider_vectors, self._resampling_frequency, realizations
                ),
                self._relative_date,
            )
        return self._provider.get_vectors_df(
            self._provider_vectors, self._resampling_frequency, realizations
        )

    def create_per_interval_and_per_day_vectors_df(
        self,
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """Get dataframe with interval delta and per day delta vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding interval delta
        or per day delta data.

        Interval delta and per day delta date is calculated with same sampling frequency as provider
        is set with. I.e. resampling frequency is given for providers supporting resampling,
        otherwise sampling frequency is fixed.

        `Input:`
        * realizations: Sequence[int] - Sequency of realization numbers to include in calculation

        `Output:`
        * dataframe with interval  vector names in columns and their cumulative data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        ---------------------
        `NOTE:`
        * Handle calculation of cumulative when raw data is added
        * See TODO in calculate_from_resampled_cumulative_vectors_df()
        """
        if not self.has_per_interval_and_per_day_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no per interval '
                "or per day vector names"
            )

        cumulative_vector_names = [
            get_cumulative_vector_name(elm)
            for elm in self._per_interval_and_per_day_vectors
            if is_per_interval_or_per_day_vector(elm)
        ]
        cumulative_vector_names = list(sorted(set(cumulative_vector_names)))

        vectors_df = self._provider.get_vectors_df(
            cumulative_vector_names, self._resampling_frequency, realizations
        )

        per_interval_and_per_day_vectors_df = pd.DataFrame()
        for vector_name in self._per_interval_and_per_day_vectors:
            cumulative_vector_name = get_cumulative_vector_name(vector_name)
            per_interval_or_per_day_vector_df = (
                calculate_from_resampled_cumulative_vectors_df(
                    vectors_df[["DATE", "REAL", cumulative_vector_name]],
                    as_per_day=vector_name.startswith("PER_DAY_"),
                )
            )
            if per_interval_and_per_day_vectors_df.empty:
                per_interval_and_per_day_vectors_df = per_interval_or_per_day_vector_df
            else:
                per_interval_and_per_day_vectors_df = pd.merge(
                    per_interval_and_per_day_vectors_df,
                    per_interval_or_per_day_vector_df,
                    how="inner",
                )

        if self._relative_date:
            return dataframe_utils.create_relative_to_date_df(
                per_interval_and_per_day_vectors_df,
                self._relative_date,
            )
        return per_interval_and_per_day_vectors_df

    def create_calculated_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        """Get dataframe with calculated vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding calculated
        data.

        Calculated vectors are created with same sampling frequency as provider is set with. I.e.
        resampling frequency is given for providers supporting resampling, otherwise sampling
        frequency is fixed.

        `Input:`
        * realizations: Sequence[int] - Sequency of realization numbers to include in calculation

        `Output:`
        * dataframe with vector names in columns and their calculated data in rows
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]
        """
        if not self.has_vector_calculator_expressions():
            raise ValueError(
                f'Assembled vector data accessor for provider "{self._name}"'
                "has no vector calculator expressions"
            )
        calculated_vectors_df = pd.DataFrame()
        for expression in self._vector_calculator_expressions:
            calculated_vector_df = create_calculated_vector_df(
                expression, self._provider, realizations, self._resampling_frequency
            )
            if calculated_vectors_df.empty:
                calculated_vectors_df = calculated_vector_df
            else:
                calculated_vectors_df = pd.merge(
                    calculated_vectors_df,
                    calculated_vector_df,
                    how="inner",
                )

        if self._relative_date:
            return dataframe_utils.create_relative_to_date_df(
                calculated_vectors_df,
                self._relative_date,
            )
        return calculated_vectors_df
