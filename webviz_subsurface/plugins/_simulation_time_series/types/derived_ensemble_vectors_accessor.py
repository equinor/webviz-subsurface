import abc
from typing import Optional, Sequence

import pandas as pd


# TODO: Rename?
# Suggestions:
# - DerivedVectorsAccessor
class DerivedEnsembleVectorsAccessor:
    @abc.abstractmethod
    def has_provider_vectors(self) -> bool:
        ...

    @abc.abstractmethod
    def has_interval_and_average_vectors(self) -> bool:
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
    def create_interval_and_average_vectors_df(
        self,
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def create_calculated_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...
