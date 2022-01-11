from datetime import datetime

import pandas as pd
from webviz_subsurface_components.VectorCalculatorWrapper import (
    ExpressionInfo,
    VariableVectorMapInfo,
)

from webviz_subsurface.plugins._simulation_time_series.types.derived_delta_ensemble_vectors_accessor_impl import (
    DerivedDeltaEnsembleVectorsAccessorImpl,
)

from ..mocks.derived_vectors_accessor_ensemble_summary_provider_mock import (
    EnsembleSummaryProviderMock,
)

# fmt: off
TEST_A_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime(2000,1,1),  1, 10.0,   500.0  ],
        [datetime(2000,2,1),  1, 20.0,   1000.0 ],
        [datetime(2000,3,1),  1, 30.0,   1500.0 ],
        [datetime(2000,4,1),  1, 40.0,   2000.0 ],
        [datetime(2000,5,1),  1, 50.0,   2500.0 ],
        [datetime(2000,1,1),  2, 60.0,   3000.0 ],
        [datetime(2000,2,1),  2, 70.0,   4000.0 ],
        [datetime(2000,3,1),  2, 80.0,   5000.0 ],
        [datetime(2000,4,1),  2, 90.0,   6000.0 ],
        [datetime(2000,5,1),  2, 100.0,  7000.0 ],
        [datetime(2000,1,1),  4, 110.0,  10000.0],
        [datetime(2000,2,1),  4, 120.0,  12000.0],
        [datetime(2000,3,1),  4, 130.0,  14000.0],
        [datetime(2000,4,1),  4, 140.0,  16000.0],
        [datetime(2000,5,1),  4, 150.0,  18000.0],
    ]
)
TEST_A_DF["DATE"] = pd.Series(TEST_A_DF["DATE"].dt.to_pydatetime(), dtype=object)

TEST_B_DF = pd.DataFrame(
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
TEST_B_DF["DATE"] = pd.Series(TEST_B_DF["DATE"].dt.to_pydatetime(), dtype=object)

# Delta between A and B DF
TEST_DELTA_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime(2000,1,1),  1, 9.0,    450.0  ],
        [datetime(2000,2,1),  1, 18.0,   900.0  ],
        [datetime(2000,3,1),  1, 27.0,   1350.0 ],
        [datetime(2000,4,1),  1, 36.0,   1800.0 ],
        [datetime(2000,5,1),  1, 45.0,   2250.0 ],
        [datetime(2000,1,1),  2, 54.0,   2700.0 ],
        [datetime(2000,2,1),  2, 63.0,   3600.0 ],
        [datetime(2000,3,1),  2, 72.0,   4500.0 ],
        [datetime(2000,4,1),  2, 81.0,   5400.0 ],
        [datetime(2000,5,1),  2, 90.0,   6300.0 ],
        [datetime(2000,1,1),  4, 99.0,   9000.0 ],
        [datetime(2000,2,1),  4, 108.0,  10800.0],
        [datetime(2000,3,1),  4, 117.0,  12600.0],
        [datetime(2000,4,1),  4, 126.0,  14400.0],
        [datetime(2000,5,1),  4, 135.0,  16200.0],
    ]
)
TEST_DELTA_DF["DATE"] = pd.Series(TEST_DELTA_DF["DATE"].dt.to_pydatetime(), dtype=object)
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
TEST_ACCESSOR = DerivedDeltaEnsembleVectorsAccessorImpl(
    name="Test accessor",
    provider_pair=(
        EnsembleSummaryProviderMock(TEST_A_DF),
        EnsembleSummaryProviderMock(TEST_B_DF),
    ),
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
    empty_provider_accessor = DerivedDeltaEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider_pair=(
            EnsembleSummaryProviderMock(pd.DataFrame()),
            EnsembleSummaryProviderMock(pd.DataFrame()),
        ),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_provider_vectors()
    assert not empty_provider_accessor.has_provider_vectors()


def test_has_interval_and_average_vectors() -> None:
    empty_provider_accessor = DerivedDeltaEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider_pair=(
            EnsembleSummaryProviderMock(pd.DataFrame()),
            EnsembleSummaryProviderMock(pd.DataFrame()),
        ),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_interval_and_average_vectors()
    assert not empty_provider_accessor.has_interval_and_average_vectors()


def test_has_vector_calculator_expressions() -> None:
    empty_provider_accessor = DerivedDeltaEnsembleVectorsAccessorImpl(
        name="Empty provider accessor",
        provider_pair=(
            EnsembleSummaryProviderMock(pd.DataFrame()),
            EnsembleSummaryProviderMock(pd.DataFrame()),
        ),
        vectors=TEST_SELECTED_VECTORS,
        expressions=None,
        resampling_frequency=None,
    )

    assert TEST_ACCESSOR.has_vector_calculator_expressions()
    assert not empty_provider_accessor.has_vector_calculator_expressions()


def test_get_provider_vectors() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).
    test_df = TEST_ACCESSOR.get_provider_vectors_df()

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    test_df["DATE"] = pd.Series(test_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert TEST_DELTA_DF.equals(test_df)
    assert TEST_DELTA_DF.columns.equals(test_df.columns)


def test_get_provider_vectors_filter_realizations() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # Verify realizations query
    expected_reals_df = (
        TEST_DELTA_DF.loc[TEST_DELTA_DF["REAL"].isin([1, 4])]
        .reset_index()
        .drop("index", axis=1)
    )

    test_df = TEST_ACCESSOR.get_provider_vectors_df(realizations=[1, 4])

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    test_df["DATE"] = pd.Series(test_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert expected_reals_df.equals(test_df)
    assert expected_reals_df.columns.equals(test_df.columns)


def test_create_interval_and_average_vectors_df() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "INTVL_B"],
        data = [
            [datetime(2000,1,1),  1, 450.0 ],
            [datetime(2000,2,1),  1, 450.0 ],
            [datetime(2000,3,1),  1, 450.0 ],
            [datetime(2000,4,1),  1, 450.0 ],
            [datetime(2000,5,1),  1, 0.0   ],
            [datetime(2000,1,1),  2, 900.0 ],
            [datetime(2000,2,1),  2, 900.0 ],
            [datetime(2000,3,1),  2, 900.0 ],
            [datetime(2000,4,1),  2, 900.0 ],
            [datetime(2000,5,1),  2, 0.0   ],
            [datetime(2000,1,1),  4, 1800.0],
            [datetime(2000,2,1),  4, 1800.0],
            [datetime(2000,3,1),  4, 1800.0],
            [datetime(2000,4,1),  4, 1800.0],
            [datetime(2000,5,1),  4, 0.0   ],
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
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "INTVL_B"],
        data = [
            [datetime(2000,1,1),  1, 450.0 ],
            [datetime(2000,2,1),  1, 450.0 ],
            [datetime(2000,3,1),  1, 450.0 ],
            [datetime(2000,4,1),  1, 450.0 ],
            [datetime(2000,5,1),  1, 0.0   ],
            [datetime(2000,1,1),  4, 1800.0],
            [datetime(2000,2,1),  4, 1800.0],
            [datetime(2000,3,1),  4, 1800.0],
            [datetime(2000,4,1),  4, 1800.0],
            [datetime(2000,5,1),  4, 0.0   ],
        ]
    )
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    created_df = TEST_ACCESSOR.create_interval_and_average_vectors_df(
        realizations=[1, 4]
    )

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    created_df["DATE"] = pd.Series(created_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert expected_df.equals(created_df)
    assert expected_df.columns.equals(created_df.columns)


def test_create_calculated_vectors_df() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "Sum A and B"],
        data = [
            [datetime(2000,1,1),  1, 459.0  ],
            [datetime(2000,2,1),  1, 918.0  ],
            [datetime(2000,3,1),  1, 1377.0 ],
            [datetime(2000,4,1),  1, 1836.0 ],
            [datetime(2000,5,1),  1, 2295.0 ],
            [datetime(2000,1,1),  2, 2754.0 ],
            [datetime(2000,2,1),  2, 3663.0 ],
            [datetime(2000,3,1),  2, 4572.0 ],
            [datetime(2000,4,1),  2, 5481.0 ],
            [datetime(2000,5,1),  2, 6390.0 ],
            [datetime(2000,1,1),  4, 9099.0 ],
            [datetime(2000,2,1),  4, 10908.0],
            [datetime(2000,3,1),  4, 12717.0],
            [datetime(2000,4,1),  4, 14526.0],
            [datetime(2000,5,1),  4, 16335.0],
        ]
    )
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    created_df = TEST_ACCESSOR.create_calculated_vectors_df()

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    created_df["DATE"] = pd.Series(created_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert expected_df.equals(created_df)
    assert expected_df.columns.equals(created_df.columns)


def test_create_calculated_vectors_df_filter_realizations() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # fmt: off
    expected_df = pd.DataFrame(
        columns = ["DATE", "REAL",  "Sum A and B"],
        data = [
            [datetime(2000,1,1),  1, 459.0  ],
            [datetime(2000,2,1),  1, 918.0  ],
            [datetime(2000,3,1),  1, 1377.0 ],
            [datetime(2000,4,1),  1, 1836.0 ],
            [datetime(2000,5,1),  1, 2295.0 ],
            [datetime(2000,1,1),  2, 2754.0 ],
            [datetime(2000,2,1),  2, 3663.0 ],
            [datetime(2000,3,1),  2, 4572.0 ],
            [datetime(2000,4,1),  2, 5481.0 ],
            [datetime(2000,5,1),  2, 6390.0 ],
        ]
    )
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    created_df = TEST_ACCESSOR.create_calculated_vectors_df(realizations=[1, 2])

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    created_df["DATE"] = pd.Series(created_df["DATE"].dt.to_pydatetime(), dtype=object)

    assert expected_df.equals(created_df)
    assert expected_df.columns.equals(created_df.columns)
