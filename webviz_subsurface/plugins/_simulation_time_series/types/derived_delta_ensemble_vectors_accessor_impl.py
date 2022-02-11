import datetime
from typing import List, Optional, Sequence, Tuple

import pandas as pd
from webviz_subsurface_components import ExpressionInfo

from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object
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


class DerivedDeltaEnsembleVectorsAccessorImpl(DerivedVectorsAccessor):
    """
    Class to create derived vector data and access these for a delta ensemble.

    The delta ensemble is represented a pair of two ensemble summary providers.

    A list of vector names are provided, and data is fetched or created based on which
    type of vectors are present in the list.

    Vector names can be regular vectors existing among vector names in the providers, Per
    Interval/Per Day vector or a calculated vector from vector calculator.

    Based on the vector type, the class provides an interface for retrieveing dataframes
    for the set of such vectors for the provider.
    """

    def __init__(
        self,
        name: str,
        provider_pair: Tuple[EnsembleSummaryProvider, EnsembleSummaryProvider],
        vectors: List[str],
        expressions: Optional[List[ExpressionInfo]] = None,
        resampling_frequency: Optional[Frequency] = None,
        relative_date: Optional[datetime.datetime] = None,
    ) -> None:
        if len(provider_pair) != 2:
            raise ValueError(
                'Expect input argument "provider_pair" to have two providers!'
                f"Got {len(provider_pair)}"
            )
        self._provider_a = provider_pair[0]
        self._provider_b = provider_pair[1]

        # Initialize base class
        _intersected_realizations = [
            elm
            for elm in self._provider_a.realizations()
            if elm in self._provider_b.realizations()
        ]
        super().__init__(_intersected_realizations)

        self._name = name
        if (
            self._provider_a.supports_resampling()
            != self._provider_b.supports_resampling()
        ):
            raise ValueError(
                f"Ensemble A and B must have same resampling support! "
                f"Ensemble A support resampling: {self._provider_a.supports_resampling()} "
                f"and Ensemble B support resampling: {self._provider_b.supports_resampling()}"
            )

        # Intersection of vectors in providers
        _accessor_vectors = [
            elm
            for elm in self._provider_a.vector_names()
            if elm in self._provider_b.vector_names()
        ]

        # Categorize vector types among the vectors in argument
        self._provider_vectors = [
            vector for vector in vectors if vector in _accessor_vectors
        ]
        self._per_interval_and_per_day_vectors = [
            vector
            for vector in vectors
            if is_per_interval_or_per_day_vector(vector)
            and get_cumulative_vector_name(vector) in _accessor_vectors
        ]
        self._vector_calculator_expressions = (
            get_selected_expressions(expressions, vectors)
            if expressions is not None
            else []
        )

        # Set resampling frequency
        self._resampling_frequency = (
            resampling_frequency
            if self._provider_a.supports_resampling()
            and self._provider_b.supports_resampling()
            else None
        )

        self._relative_date = relative_date

    def __create_delta_ensemble_vectors_df(
        self,
        vector_names: List[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        Get vectors dataframe with delta vectors for ensemble A and B, for common realizations

        `Return:` Dataframe with delta ensemble data for common vectors and realizations in ensemble
        A and B.

        `Output:`
        * DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]

        `Input:`
        * vector_names: List[str] - List of vector names to get data for
        * resampling_frequency: Optional[Frequency] - Optional resampling frequency
        * realizations: Optional[Sequence[int]] - Optional sequence of realization numbers for
        vectors

        NOTE:
        - Performs "inner join". Only obtain matching index ["DATE", "REAL"] - i.e "DATE"-"REAL"
        combination present in only one vector -> neglected
        - Ensures equal dates samples and realizations by dropping nan-values
        """

        if not vector_names:
            raise ValueError("List of requested vector names is empty")

        # NOTE: index order ["DATE","REAL"] to obtain column order when
        # performing reset_index() later
        ensemble_a_vectors_df = self._provider_a.get_vectors_df(
            vector_names, resampling_frequency, realizations
        ).set_index(["DATE", "REAL"])
        ensemble_b_vectors_df = self._provider_b.get_vectors_df(
            vector_names, resampling_frequency, realizations
        ).set_index(["DATE", "REAL"])

        # Reset index, sort values by "REAL" and thereafter by "DATE" to
        # group realizations and order by date
        ensembles_delta_vectors_df = (
            ensemble_a_vectors_df.sub(ensemble_b_vectors_df)
            .dropna(axis=0, how="any")
            .reset_index()
            .sort_values(["REAL", "DATE"], ignore_index=True)
        )

        make_date_column_datetime_object(ensembles_delta_vectors_df)

        return ensembles_delta_vectors_df

    def has_provider_vectors(self) -> bool:
        return len(self._provider_vectors) > 0

    def has_per_interval_and_per_day_vectors(self) -> bool:
        return len(self._per_interval_and_per_day_vectors) > 0

    def has_vector_calculator_expressions(self) -> bool:
        return len(self._vector_calculator_expressions) > 0

    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        """
        Get vectors dataframe with delta vectors for ensemble A and B, for common realizations and
        selected vectors

        `Return:` Dataframe with delta ensemble data for common vectors and realizations in ensemble
        A and B.

        `Output:`
        * DataFrame with columns ["DATE", "REAL", vector1, ..., vectorN]
        """
        if not self.has_provider_vectors():
            raise ValueError(
                f'Vector data handler for provider "{self._name}" has no provider vectors'
            )

        if self._relative_date:
            return dataframe_utils.create_relative_to_date_df(
                self.__create_delta_ensemble_vectors_df(
                    self._provider_vectors, self._resampling_frequency, realizations
                ),
                self._relative_date,
            )
        return self.__create_delta_ensemble_vectors_df(
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

        vectors_df = self.__create_delta_ensemble_vectors_df(
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

        The calculated vectors for delta ensembles are created by first creating the calculated
        vector data for ensemble A and B separately, and thereafter subtracting the data in ensemble
        B from A. Thereby one obtain creating the delta ensemble of the resulting calculated
        vectors.

        Calculated vectors are created with same sampling frequency as providers is set with. I.e.
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

        provider_a_calculated_vectors_df = pd.DataFrame()
        provider_b_calculated_vectors_df = pd.DataFrame()
        for expression in self._vector_calculator_expressions:
            provider_a_calculated_vector_df = create_calculated_vector_df(
                expression, self._provider_a, realizations, self._resampling_frequency
            )
            provider_b_calculated_vector_df = create_calculated_vector_df(
                expression, self._provider_b, realizations, self._resampling_frequency
            )

            if (
                provider_a_calculated_vector_df.empty
                or provider_b_calculated_vector_df.empty
            ):
                # TODO: Consider raising ValueError of vector calculation in one provider fails?
                # If both fails, it's okay?
                continue

            def __inner_merge_dataframes(
                first: pd.DataFrame, second: pd.DataFrame
            ) -> pd.DataFrame:
                if first.empty:
                    return second
                return pd.merge(first, second, how="inner")

            provider_a_calculated_vectors_df = __inner_merge_dataframes(
                provider_a_calculated_vectors_df, provider_a_calculated_vector_df
            )
            provider_b_calculated_vectors_df = __inner_merge_dataframes(
                provider_b_calculated_vectors_df, provider_b_calculated_vector_df
            )

        # NOTE: index order ["DATE","REAL"] to obtain column order when
        # performing reset_index() later
        provider_a_calculated_vectors_df.set_index(["DATE", "REAL"], inplace=True)
        provider_b_calculated_vectors_df.set_index(["DATE", "REAL"], inplace=True)

        # Reset index, sort values by "REAL" and thereafter by "DATE" to
        # group realizations and order by date
        delta_ensemble_calculated_vectors_df = (
            provider_a_calculated_vectors_df.sub(provider_b_calculated_vectors_df)
            .dropna(axis=0, how="any")
            .reset_index()
            .sort_values(["REAL", "DATE"], ignore_index=True)
        )

        make_date_column_datetime_object(delta_ensemble_calculated_vectors_df)

        if self._relative_date:
            return dataframe_utils.create_relative_to_date_df(
                delta_ensemble_calculated_vectors_df,
                self._relative_date,
            )
        return delta_ensemble_calculated_vectors_df
