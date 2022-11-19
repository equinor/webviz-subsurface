import abc
from typing import List, Optional, Sequence

import pandas as pd


class DerivedVectorsAccessor:
    def __init__(self, accessor_realizations: List[int]) -> None:
        self._accessor_realizations: List[int] = accessor_realizations

    @abc.abstractmethod
    def has_provider_vectors(self) -> bool:
        ...

    @abc.abstractmethod
    def has_per_interval_and_per_day_vectors(self) -> bool:
        ...

    @abc.abstractmethod
    def has_vector_calculator_expressions(self) -> bool:
        ...

    @abc.abstractmethod
    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def create_per_interval_and_per_day_vectors_df(
        self,
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def create_calculated_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    def create_valid_realizations_query(
        self, selected_realizations: List[int]
    ) -> Optional[List[int]]:
        """Create realizations query for accessor based on selected realizations.

        `Returns:`
        - None - If all realizations for accessor is selected, i.e. the query is non-filtering
        - List[int] - List of realization numbers existing for the accessor - empty list
        is returned if no realizations exist.
        """
        if set(self._accessor_realizations).issubset(set(selected_realizations)):
            return None
        return [
            realization
            for realization in selected_realizations
            if realization in self._accessor_realizations
        ]
