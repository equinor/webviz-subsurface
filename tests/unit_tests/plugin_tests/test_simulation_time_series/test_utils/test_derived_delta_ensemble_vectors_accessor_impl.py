import datetime

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal
from webviz_subsurface_components.VectorCalculatorWrapper import (
    ExpressionInfo,
    VariableVectorMapInfo,
)

from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object

# pylint: disable = line-too-long
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._utils.derived_vectors_accessor.derived_delta_ensemble_vectors_accessor_impl import (
    DerivedDeltaEnsembleVectorsAccessorImpl,
)

from ..mocks.derived_vectors_accessor_ensemble_summary_provider_mock import (
    EnsembleSummaryProviderMock,
)

# *******************************************************************
#####################################################################
#
# CONFIGURE TESTDATA
#
#####################################################################
# *******************************************************************

# fmt: off
# Ensemble A
INPUT_A_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime.datetime(2000,1,1),  1, 10.0,   500.0  ],
        [datetime.datetime(2000,2,1),  1, 20.0,   1000.0 ],
        [datetime.datetime(2000,3,1),  1, 30.0,   1500.0 ],
        [datetime.datetime(2000,1,1),  2, 60.0,   3000.0 ],
        [datetime.datetime(2000,2,1),  2, 70.0,   4000.0 ],
        [datetime.datetime(2000,3,1),  2, 80.0,   5000.0 ],
        [datetime.datetime(2000,1,1),  4, 110.0,  10000.0],
        [datetime.datetime(2000,2,1),  4, 120.0,  12000.0],
        [datetime.datetime(2000,3,1),  4, 130.0,  14000.0],
    ]
)

# Ensemble B
INPUT_B_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime.datetime(2000,1,1),  1, 1.0,   50.0  ],
        [datetime.datetime(2000,2,1),  1, 2.0,   100.0 ],
        [datetime.datetime(2000,3,1),  1, 3.0,   150.0 ],
        [datetime.datetime(2000,1,1),  2, 6.0,   300.0 ],
        [datetime.datetime(2000,2,1),  2, 7.0,   400.0 ],
        [datetime.datetime(2000,3,1),  2, 8.0,   500.0 ],
        [datetime.datetime(2000,1,1),  4, 11.0,  1000.0],
        [datetime.datetime(2000,2,1),  4, 12.0,  1200.0],
        [datetime.datetime(2000,3,1),  4, 13.0,  1400.0],
    ]
)

# Delta between A and B DF (A-B)
EXPECTED_DELTA_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "A", "B"],
    data = [
        [datetime.datetime(2000,1,1),  1, 9.0,    450.0  ],
        [datetime.datetime(2000,2,1),  1, 18.0,   900.0  ],
        [datetime.datetime(2000,3,1),  1, 27.0,   1350.0 ],
        [datetime.datetime(2000,1,1),  2, 54.0,   2700.0 ],
        [datetime.datetime(2000,2,1),  2, 63.0,   3600.0 ],
        [datetime.datetime(2000,3,1),  2, 72.0,   4500.0 ],
        [datetime.datetime(2000,1,1),  4, 99.0,   9000.0 ],
        [datetime.datetime(2000,2,1),  4, 108.0,  10800.0],
        [datetime.datetime(2000,3,1),  4, 117.0,  12600.0],
    ]
)

# PER_INTVL_ calc for col "B" of Delta
EXPECTED_DELTA_INVTL_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "PER_INTVL_B"],
    data = [
        [datetime.datetime(2000,1,1),  1, 450.0 ],
        [datetime.datetime(2000,2,1),  1, 450.0 ],
        [datetime.datetime(2000,3,1),  1, 0.0   ],
        [datetime.datetime(2000,1,1),  2, 900.0 ],
        [datetime.datetime(2000,2,1),  2, 900.0 ],
        [datetime.datetime(2000,3,1),  2, 0.0   ],
        [datetime.datetime(2000,1,1),  4, 1800.0],
        [datetime.datetime(2000,2,1),  4, 1800.0],
        [datetime.datetime(2000,3,1),  4, 0.0   ],
    ]
)

# Sum of col "A" and "B" in Delta
EXPECTED_SUM_A_AND_B_DF = pd.DataFrame(
    columns = ["DATE", "REAL",  "Sum A and B"],
    data = [
        [datetime.datetime(2000,1,1),  1, 459.0  ],
        [datetime.datetime(2000,2,1),  1, 918.0  ],
        [datetime.datetime(2000,3,1),  1, 1377.0 ],
        [datetime.datetime(2000,1,1),  2, 2754.0 ],
        [datetime.datetime(2000,2,1),  2, 3663.0 ],
        [datetime.datetime(2000,3,1),  2, 4572.0 ],
        [datetime.datetime(2000,1,1),  4, 9099.0 ],
        [datetime.datetime(2000,2,1),  4, 10908.0],
        [datetime.datetime(2000,3,1),  4, 12717.0],
    ]
)
make_date_column_datetime_object(INPUT_A_DF)
make_date_column_datetime_object(INPUT_B_DF)
make_date_column_datetime_object(EXPECTED_DELTA_DF)
make_date_column_datetime_object(EXPECTED_DELTA_INVTL_DF)
make_date_column_datetime_object(EXPECTED_SUM_A_AND_B_DF)


# Dates AFTER year 2262!
AFTER_2262_DATES = pd.Series(
    [
        datetime.datetime(2265,1,1),
        datetime.datetime(2265,2,1),
        datetime.datetime(2265,3,1),
        datetime.datetime(2265,1,1),
        datetime.datetime(2265,2,1),
        datetime.datetime(2265,3,1),
        datetime.datetime(2265,1,1),
        datetime.datetime(2265,2,1),
        datetime.datetime(2265,3,1),
    ]
)
# NOTE: datetime.datetime after year 2262 is not converted to pd.Timestamp, thus
# no need to make date column datetime object
INPUT_A_AFTER_2262_DF = INPUT_A_DF.copy()
INPUT_A_AFTER_2262_DF["DATE"] = AFTER_2262_DATES
INPUT_B_AFTER_2262_DF = INPUT_B_DF.copy()
INPUT_B_AFTER_2262_DF["DATE"] = AFTER_2262_DATES
EXPECTED_DELTA_AFTER_2262_DF = EXPECTED_DELTA_DF.copy()
EXPECTED_DELTA_AFTER_2262_DF["DATE"] = AFTER_2262_DATES
EXPECTED_DELTA_INVTL_AFTER_2262_DF = EXPECTED_DELTA_INVTL_DF.copy()
EXPECTED_DELTA_INVTL_AFTER_2262_DF["DATE"] = AFTER_2262_DATES
EXPECTED_SUM_A_AND_B_AFTER_2262_DF = EXPECTED_SUM_A_AND_B_DF.copy()
EXPECTED_SUM_A_AND_B_AFTER_2262_DF["DATE"] = AFTER_2262_DATES

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

TEST_ACCESSOR = DerivedDeltaEnsembleVectorsAccessorImpl(
    name="Test accessor",
    provider_pair=(
        EnsembleSummaryProviderMock(INPUT_A_DF),
        EnsembleSummaryProviderMock(INPUT_B_DF),
    ),
    vectors=["A", "B", "PER_INTVL_B", "Sum A and B"],
    expressions=[TEST_EXPRESSION],
    resampling_frequency=None,
)

TEST_AFTER_2262_ACCESSOR = DerivedDeltaEnsembleVectorsAccessorImpl(
    name="Test 2262 accessor",
    provider_pair=(
        EnsembleSummaryProviderMock(INPUT_A_AFTER_2262_DF),
        EnsembleSummaryProviderMock(INPUT_B_AFTER_2262_DF),
    ),
    vectors=["A", "B", "PER_INTVL_B", "Sum A and B"],
    expressions=[TEST_EXPRESSION],
    resampling_frequency=None,
)

TEST_EMPTY_ACCESSOR = DerivedDeltaEnsembleVectorsAccessorImpl(
    name="Empty provider accessor",
    provider_pair=(
        EnsembleSummaryProviderMock(pd.DataFrame()),
        EnsembleSummaryProviderMock(pd.DataFrame()),
    ),
    vectors=["A", "B", "PER_INTVL_B", "Sum A and B"],
    expressions=None,
    resampling_frequency=None,
)

# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************

TEST_STATUS_CASES = [
    pytest.param(TEST_ACCESSOR, True),
    pytest.param(TEST_AFTER_2262_ACCESSOR, True),
    pytest.param(TEST_EMPTY_ACCESSOR, False),
]
TEST_GET_VECTOR_CASES = [
    pytest.param(TEST_ACCESSOR, EXPECTED_DELTA_DF),
    pytest.param(TEST_AFTER_2262_ACCESSOR, EXPECTED_DELTA_AFTER_2262_DF),
]
TEST_CREATE_PER_INTVL_PER_DAY_VECTOR_CASES = [
    pytest.param(TEST_ACCESSOR, EXPECTED_DELTA_INVTL_DF),
    pytest.param(TEST_AFTER_2262_ACCESSOR, EXPECTED_DELTA_INVTL_AFTER_2262_DF),
]
TEST_CREATE_CALCULATED_VECTOR_CASES = [
    pytest.param(TEST_ACCESSOR, EXPECTED_SUM_A_AND_B_DF),
    pytest.param(TEST_AFTER_2262_ACCESSOR, EXPECTED_SUM_A_AND_B_AFTER_2262_DF),
]


@pytest.mark.parametrize("test_accessor, expected_state", TEST_STATUS_CASES)
def test_has_provider_vectors(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_state: bool
) -> None:
    assert test_accessor.has_provider_vectors() == expected_state


@pytest.mark.parametrize("test_accessor, expected_state", TEST_STATUS_CASES)
def test_has_per_interval_and_per_day_vectors(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_state: bool
) -> None:
    assert test_accessor.has_per_interval_and_per_day_vectors() == expected_state


@pytest.mark.parametrize("test_accessor, expected_state", TEST_STATUS_CASES)
def test_has_vector_calculator_expressions(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_state: bool
) -> None:
    assert test_accessor.has_vector_calculator_expressions() == expected_state


@pytest.mark.parametrize("test_accessor, expected_df", TEST_GET_VECTOR_CASES)
def test_get_provider_vectors(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    assert_frame_equal(expected_df, test_accessor.get_provider_vectors_df())


@pytest.mark.parametrize("test_accessor, expected_df", TEST_GET_VECTOR_CASES)
def test_get_provider_vectors_filter_realizations(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    # Filter realizations
    expected_reals_df = (
        expected_df.loc[expected_df["REAL"].isin([2, 4])]
        .reset_index()
        .drop("index", axis=1)
    )

    test_df = test_accessor.get_provider_vectors_df(realizations=[2, 4])

    assert_frame_equal(expected_reals_df, test_df)
    assert list(set(test_df["REAL"].values)) == [2, 4]


@pytest.mark.parametrize(
    "test_accessor, expected_df", TEST_CREATE_PER_INTVL_PER_DAY_VECTOR_CASES
)
def test_create_per_interval_and_per_day_vectors_df(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    assert_frame_equal(
        expected_df, test_accessor.create_per_interval_and_per_day_vectors_df()
    )


@pytest.mark.parametrize(
    "test_accessor, expected_df", TEST_CREATE_PER_INTVL_PER_DAY_VECTOR_CASES
)
def test_create_per_interval_and_per_day_vectors_df_filter_realizations(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    # Filter realizations
    expected_reals_df = (
        expected_df.loc[expected_df["REAL"].isin([1, 4])]
        .reset_index()
        .drop("index", axis=1)
    )

    test_df = test_accessor.create_per_interval_and_per_day_vectors_df(
        realizations=[1, 4]
    )

    assert_frame_equal(expected_reals_df, test_df)
    assert list(set(test_df["REAL"].values)) == [1, 4]


@pytest.mark.parametrize(
    "test_accessor, expected_df", TEST_CREATE_CALCULATED_VECTOR_CASES
)
def test_create_calculated_vectors_df(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    assert_frame_equal(expected_df, test_accessor.create_calculated_vectors_df())


@pytest.mark.parametrize(
    "test_accessor, expected_df", TEST_CREATE_CALCULATED_VECTOR_CASES
)
def test_create_calculated_vectors_df_filter_realizations(
    test_accessor: DerivedDeltaEnsembleVectorsAccessorImpl, expected_df: pd.DataFrame
) -> None:
    # Filter realizations
    expected_reals_df = (
        expected_df.loc[expected_df["REAL"].isin([1, 2])]
        .reset_index()
        .drop("index", axis=1)
    )

    test_df = test_accessor.create_calculated_vectors_df(realizations=[1, 2])

    assert_frame_equal(expected_reals_df, test_df)
    assert list(set(test_df["REAL"].values)) == [1, 2]
