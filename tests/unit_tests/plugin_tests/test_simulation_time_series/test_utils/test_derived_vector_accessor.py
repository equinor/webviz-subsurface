from typing import Optional, Sequence

import pandas as pd

# pylint: disable=line-too-long
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._utils.derived_vectors_accessor.derived_vectors_accessor import (
    DerivedVectorsAccessor,
)


class DerivedVectorsAccessorMock(DerivedVectorsAccessor):
    #####################################################e
    #
    # Interface methods raise NotImplementedError
    #
    #####################################################

    def has_provider_vectors(self) -> bool:
        raise NotImplementedError("Method not implemented for mock!")

    def has_per_interval_and_per_day_vectors(self) -> bool:
        raise NotImplementedError("Method not implemented for mock!")

    def has_vector_calculator_expressions(self) -> bool:
        raise NotImplementedError("Method not implemented for mock!")

    def get_provider_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        raise NotImplementedError("Method not implemented for mock!")

    def create_per_interval_and_per_day_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        raise NotImplementedError("Method not implemented for mock!")

    def create_calculated_vectors_df(
        self, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        raise NotImplementedError("Method not implemented for mock!")


def test_create_valid_realizations_query() -> None:
    realizations = [2, 3, 4, 6, 7, 8]
    test_accessor = DerivedVectorsAccessorMock(accessor_realizations=realizations)

    # Filter query (get valid realization numbers)
    assert test_accessor.create_valid_realizations_query([1, 2, 3]) == [2, 3]
    assert test_accessor.create_valid_realizations_query([3, 4, 5, 6]) == [3, 4, 6]
    assert test_accessor.create_valid_realizations_query([3, 2, 7, 6]) == [3, 2, 7, 6]
    assert test_accessor.create_valid_realizations_query([1, 5]) == []

    # When all realizations are selected -> no filter, i.e. None
    assert test_accessor.create_valid_realizations_query(realizations) is None
    assert (
        test_accessor.create_valid_realizations_query([1, 2, 3, 4, 5, 6, 7, 8]) is None
    )
