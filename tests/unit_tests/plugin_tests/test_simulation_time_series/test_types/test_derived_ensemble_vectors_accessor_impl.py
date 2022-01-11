from datetime import datetime

import pandas as pd
from webviz_subsurface_components.VectorCalculatorWrapper import (
    ExpressionInfo,
    VariableVectorMapInfo,
)

from webviz_subsurface.plugins._simulation_time_series.types.derived_ensemble_vectors_accessor_impl import (
    DerivedEnsembleVectorsAccessorImpl,
)

from ..mocks.derived_vectors_accessor_ensemble_summary_provider_mock import (
    EnsembleSummaryProviderMock,
)

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
TEST_DF["DATE"] = pd.Series([ts.to_pydatetime() for ts in TEST_DF["DATE"]], dtype="object")
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
    name="Test accessor",
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
    expected_reals_df = (
        TEST_DF.loc[TEST_DF["REAL"].isin([1, 4])].reset_index().drop("index", axis=1)
    )
    assert expected_reals_df.equals(
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
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    created_df = TEST_ACCESSOR.create_interval_and_average_vectors_df()

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    created_df["DATE"] = pd.Series(created_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert expected_df.equals(created_df)
    assert expected_df.columns.equals(created_df.columns)


def test_create_interval_and_average_vectors_df_filter_realizations() -> None:
    # TODO: Fix unit test when issue with datetime.datetime -> Timestamp
    # when df.set_index() is utilized. Thus df["DATE"] is of Timestamp when
    # df.reset_index(level=["DATE"])

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "INTVL_B"],
        data = [
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
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    created_reals_df = TEST_ACCESSOR.create_interval_and_average_vectors_df(
        realizations=[2, 4]
    )

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    created_reals_df["DATE"] = pd.Series(
        created_reals_df["DATE"].dt.to_pydatetime(), dtype=object
    )

    assert expected_df.equals(created_reals_df)
    assert expected_df.columns.equals(created_reals_df.columns)


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
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    assert expected_df.equals(TEST_ACCESSOR.create_calculated_vectors_df())
    assert expected_df.columns.equals(
        TEST_ACCESSOR.create_calculated_vectors_df().columns
    )

    # Verify realizations query
    expected_reals_df = (
        expected_df.loc[expected_df["REAL"].isin([2, 4])]
        .reset_index()
        .drop("index", axis=1)
    )
    assert expected_reals_df.equals(
        TEST_ACCESSOR.create_calculated_vectors_df(realizations=[2, 4])
    )
