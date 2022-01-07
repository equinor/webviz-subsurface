from datetime import datetime
from typing import List, Optional, Sequence

import pandas as pd
from webviz_subsurface_components.VectorCalculatorWrapper import (
    ExpressionInfo,
    VariableVectorMapInfo,
)

from webviz_subsurface._providers import Frequency
from webviz_subsurface.plugins._simulation_time_series.types.derived_ensemble_vectors_accessor_impl import (
    DerivedEnsembleVectorsAccessorImpl,
)

from ..mocks.ensemble_summary_provider_dummy import EnsembleSummaryProviderDummy


class EnsembleSummaryProviderMock(EnsembleSummaryProviderDummy):
    """Mock implementation of EnsembleSummaryProvider for testing derived
    ensemble vectors accessor.

    Implements necessary methods for obtaining wanted test data
    """

    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__()
        self._df = df
        self._vectors: List[str] = [elm for elm in df.columns if elm not in ["DATE", "REAL"]]
        self._realizations: List[int] = list(df["REAL"]) if "REAL" in df.columns else []

    #####################################
    #
    # Override methods
    #
    #####################################
    def supports_resampling(self) -> bool:
        return False

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_names(self) -> List[str]:
        return self._vectors

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        __resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        for elm in vector_names:
            if elm not in self._vectors:
                raise ValueError(f'Requested vector "{elm}" not among provider vectors!')
        if realizations:
            return self._df[["DATE", "REAL"] + list(vector_names)].loc[
                self._df["REAL"].isin(realizations)
            ]
        return self._df[["DATE", "REAL"] + list(vector_names)]


# fmt: off
TEST_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime(2000,1,1),  1, 1.0,   50.0  ],
        [datetime(2000,2,1),  1, 2.0,   100.0 ],
        [datetime(2000,3,1),  1, 3.0,   150.0 ],
        [datetime(2000,4,1),  1, 4.0,   200.0 ],
        [datetime(2000,5,1),  1, 5.0,   250.0 ],
        [datetime(2000,1,1),  2, 6.0,   300.0 ],
        [datetime(2000,2,1),  2, 7.0,   400.0 ],
        [datetime(2000,3,1),  2, 8.0,   500.0 ],
        [datetime(2000,4,1),  2, 9.0,   600.0 ],
        [datetime(2000,5,1),  2, 10.0,  700.0 ],
        [datetime(2000,1,1),  4, 11.0,  1000.0],
        [datetime(2000,2,1),  4, 12.0,  1200.0],
        [datetime(2000,3,1),  4, 13.0,  1400.0],
        [datetime(2000,4,1),  4, 14.0,  1600.0],
        [datetime(2000,5,1),  4, 15.0,  1800.0],
    ]
)
# fmt: on
TEST_EXPRESSION = ExpressionInfo(
    name="Sum A and B",
    expression="x+y",
    id="TestId",
    variableVectorMap=[
        VariableVectorMapInfo(variableName="x", vectorName=["A"]),
        VariableVectorMapInfo(variableName="y", vectorName=["B"]),
    ],
    isValid=True,
    isDeletable=False,
)
TEST_SELECTED_VECTORS = ["A", "B", "INTVL_B", "Sum A and B"]
TEST_ACCESSOR = DerivedEnsembleVectorsAccessorImpl(
    name="First accessor",
    provider=EnsembleSummaryProviderMock(TEST_DF),
    vectors=TEST_SELECTED_VECTORS,
    expressions=[TEST_EXPRESSION],
    resampling_frequency=None,
)

#####################################################################
#
# UNIT TESTS
#
#####################################################################


def test_has_provider_vectors() -> None:
    empty_provider_accessor = DerivedEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider=EnsembleSummaryProviderMock(pd.DataFrame()),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_provider_vectors()
    assert not empty_provider_accessor.has_provider_vectors()


def test_has_interval_and_average_vectors() -> None:
    empty_provider_accessor = DerivedEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider=EnsembleSummaryProviderMock(pd.DataFrame()),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_interval_and_average_vectors()
    assert not empty_provider_accessor.has_interval_and_average_vectors()


def test_has_vector_calculator_expressions() -> None:
    empty_provider_accessor = DerivedEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider=EnsembleSummaryProviderMock(pd.DataFrame()),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_vector_calculator_expressions()
    assert not empty_provider_accessor.has_vector_calculator_expressions()


def test_get_provider_vectors() -> None:
    assert TEST_DF.equals(TEST_ACCESSOR.get_provider_vectors_df())
    assert TEST_DF.columns.equals(TEST_ACCESSOR.get_provider_vectors_df().columns)

    # Verify realizations query
    assert TEST_DF.loc[TEST_DF["REAL"].isin([1, 4])].equals(
        TEST_ACCESSOR.get_provider_vectors_df(realizations=[1, 4])
    )


def test_create_interval_and_average_vectors_df() -> None:
    # TODO: Fix unit test when issue with datetime.datetime -> Timestamp
    # when df.set_index() is utilized. Thus df["DATE"] is of Timestamp when
    # df.reset_index(level=["DATE"])

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "INTVL_B"],
        data = [
            [datetime(2000,1,1),  1, 50.0 ],
            [datetime(2000,2,1),  1, 50.0 ],
            [datetime(2000,3,1),  1, 50.0 ],
            [datetime(2000,4,1),  1, 50.0 ],
            [datetime(2000,5,1),  1, 0.0  ],
            [datetime(2000,1,1),  2, 100.0],
            [datetime(2000,2,1),  2, 100.0],
            [datetime(2000,3,1),  2, 100.0],
            [datetime(2000,4,1),  2, 100.0],
            [datetime(2000,5,1),  2, 0.0  ],
            [datetime(2000,1,1),  4, 200.0],
            [datetime(2000,2,1),  4, 200.0],
            [datetime(2000,3,1),  4, 200.0],
            [datetime(2000,4,1),  4, 200.0],
            [datetime(2000,5,1),  4, 0.0  ],
        ]
    )
    # fmt: on

    assert expected_df.equals(TEST_ACCESSOR.create_interval_and_average_vectors_df())


def test_create_calculated_vectors_df() -> None:
    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "Sum A and B"],
        data = [
            [datetime(2000,1,1),  1, 51.0  ],
            [datetime(2000,2,1),  1, 102.0 ],
            [datetime(2000,3,1),  1, 153.0 ],
            [datetime(2000,4,1),  1, 204.0 ],
            [datetime(2000,5,1),  1, 255.0 ],
            [datetime(2000,1,1),  2, 306.0 ],
            [datetime(2000,2,1),  2, 407.0 ],
            [datetime(2000,3,1),  2, 508.0 ],
            [datetime(2000,4,1),  2, 609.0 ],
            [datetime(2000,5,1),  2, 710.0 ],
            [datetime(2000,1,1),  4, 1011.0],
            [datetime(2000,2,1),  4, 1212.0],
            [datetime(2000,3,1),  4, 1413.0],
            [datetime(2000,4,1),  4, 1614.0],
            [datetime(2000,5,1),  4, 1815.0],
        ]
    )
    # fmt: ON

    assert expected_df.equals(TEST_ACCESSOR.create_calculated_vectors_df())
    assert expected_df.columns.equals(TEST_ACCESSOR.create_calculated_vectors_df().columns)

    # Verify realizations query
    assert expected_df.loc[expected_df["REAL"].isin([2, 4])].equals(
        TEST_ACCESSOR.create_calculated_vectors_df(realizations=[2, 4])
    )
