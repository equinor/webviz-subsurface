import datetime
from typing import Type

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._utils.dataframe_utils import (
    assert_date_column_is_datetime_object,
    make_date_column_datetime_object,
)

# *******************************************************
#########################################################
#
# SETUP OF INPUT DATAFRAMES FOR TESTS
#
#########################################################
# *******************************************************
# fmt: off
INPUT_EMPTY_DF = pd.DataFrame()
INPUT_NO_ROWS_DF = pd.DataFrame(columns=["DATE", "A"])
INPUT_TIMESTAMP_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [pd.Timestamp(2000, 1, 15), 1.0],
        [pd.Timestamp(2000, 2, 15), 1.0]],
)
INPUT_TIMESTAMP_DATETIME_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [pd.Timestamp(2000, 1, 1),       1.0],  # pd.Timestamp detected in df["DATE"][0]
        [datetime.datetime(2263, 2, 15), 1.0],
    ],
)
INPUT_DATETIME_TIMESTAMP_DF = pd.DataFrame(
    data=[
        [datetime.datetime(2263, 2, 1), 1.0],
        [pd.Timestamp(2000, 1, 1),      1.0],  # pd.Timestamp NOT detected in df["DATE"][1]
    ],
    columns=["DATE", "A"],
)
INPUT_DATETIME_YEAR_2020_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.datetime(2020, 1, 15), 1.0],
        [datetime.datetime(2020, 2, 15), 2.0],
        [datetime.datetime(2020, 3, 15), 3.0],
    ],
)
INPUT_DATETIME_YEAR_2020_DF["DATE"] = pd.Series(
    INPUT_DATETIME_YEAR_2020_DF["DATE"].dt.to_pydatetime(), dtype=object
) # Converting "DATE"-column to datetime.datetime after construct

INPUT_DATETIME_YEAR_2263_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.datetime(2263, 1, 15), 1.0],
        [datetime.datetime(2263, 2, 15), 2.0],
        [datetime.datetime(2263, 3, 15), 3.0],
    ],
)
INPUT_DATETIME_YEAR_2263_INCONSISTENT_INDEX_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.datetime(2263, 1, 15), 1.0],
        [datetime.datetime(2263, 2, 15), 2.0],
        [datetime.datetime(2263, 3, 15), 3.0],
    ],
    index = [2,5,9]
)
INPUT_TIMESTAMP_YEAR_2020_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [pd.Timestamp(2020, 1, 15), 1.0],
        [pd.Timestamp(2020, 2, 15), 2.0],
        [pd.Timestamp(2020, 3, 15), 3.0],
    ],
)

INPUT_DATE_YEAR_2020_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.date(2020, 1, 15), 1.0],
        [datetime.date(2020, 2, 15), 2.0],
        [datetime.date(2020, 3, 15), 3.0],
    ],
)
# fmt: on

# *******************************************************
#########################################################
#
# TESTING OF: assert_date_column_is_datetime_object()
#
#########################################################
# *******************************************************
TEST_CASES_ERROR_RAISED = [
    pytest.param(INPUT_EMPTY_DF, 'df does not contain column "DATE"'),
    pytest.param(
        INPUT_NO_ROWS_DF,
        'DataFrame does not contain rows of data, cannot ensure correct type in "DATE" column!',
    ),
    pytest.param(
        INPUT_TIMESTAMP_DF,
        '"DATE"-column in dataframe is not on datetime.datetime format!',
    ),
    pytest.param(
        INPUT_TIMESTAMP_DATETIME_DF,
        '"DATE"-column in dataframe is not on datetime.datetime format!',
    ),
]
TEST_CASES_NO_ERROR = [
    pytest.param(INPUT_DATETIME_YEAR_2020_DF),
    pytest.param(INPUT_DATETIME_YEAR_2263_DF),
    pytest.param(INPUT_DATETIME_TIMESTAMP_DF),
    pytest.param(INPUT_DATETIME_YEAR_2263_INCONSISTENT_INDEX_DF),
]


@pytest.mark.parametrize("input_df, expected_msg", TEST_CASES_ERROR_RAISED)
def test_assert_date_column_is_datetime_object_error_raised(
    input_df: pd.DataFrame, expected_msg: str
) -> None:
    with pytest.raises(ValueError) as err:
        assert_date_column_is_datetime_object(input_df)
    assert str(err.value) == expected_msg


@pytest.mark.parametrize("input_df", TEST_CASES_NO_ERROR)
def test_assert_date_column_is_datetime_object_no_errors(
    input_df: pd.DataFrame,
) -> None:
    """Test cases where first element in "DATE" column is datetime.datetime"""
    try:
        assert_date_column_is_datetime_object(input_df)

    # pylint: disable = bare-except
    except:
        pytest.fail("Excpected no raise of ERROR!")


# *******************************************************
########################################################
#
# TESTING OF: make_date_column_datetime_object()
#
########################################################
# *******************************************************
EXPECTED_YEAR_2020_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.datetime(2020, 1, 15), 1.0],
        [datetime.datetime(2020, 2, 15), 2.0],
        [datetime.datetime(2020, 3, 15), 3.0],
    ],
)
# Convert "DATE" column to datetime.datetime format as DataFrame constructor
# converts datetime.datetime to pd.Timestamp
EXPECTED_YEAR_2020_DF["DATE"] = pd.Series(
    EXPECTED_YEAR_2020_DF["DATE"].dt.to_pydatetime(), dtype=object
)

# Constructor not converting datetime.datetime for year > 2262 to pd.Timestamp
EXPECTED_YEAR_2263_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [datetime.datetime(2263, 1, 15), 1.0],
        [datetime.datetime(2263, 2, 15), 2.0],
        [datetime.datetime(2263, 3, 15), 3.0],
    ],
)


TEST_VALID_CASES = [
    pytest.param(INPUT_DATETIME_YEAR_2020_DF, EXPECTED_YEAR_2020_DF),
    pytest.param(INPUT_TIMESTAMP_YEAR_2020_DF, EXPECTED_YEAR_2020_DF),
    pytest.param(INPUT_DATETIME_YEAR_2263_DF, EXPECTED_YEAR_2263_DF),
    pytest.param(INPUT_NO_ROWS_DF, INPUT_NO_ROWS_DF),
]

TEST_INVALID_CASES = [
    pytest.param(INPUT_EMPTY_DF, 'df does not contain column "DATE"', ValueError),
    pytest.param(
        INPUT_DATE_YEAR_2020_DF,
        f'Column "DATE" of type {datetime.date} is not handled!',
        ValueError,
    ),
    pytest.param(
        INPUT_TIMESTAMP_DATETIME_DF,
        "Can only use .dt accessor with datetimelike values",
        AttributeError,
    ),
]


def _verify_expected_df_date_column_data(df: pd.DataFrame) -> None:
    """Verify dataframe contains column named "DATE" and that
    each row in column is of type datetime.datetime.

    NOTE: Can be 0 rows
    """
    assert "DATE" in df.columns
    for row in df["DATE"]:
        # pylint: disable = unidiomatic-typecheck
        assert type(row) == datetime.datetime


@pytest.mark.parametrize("input_df, expected_df", TEST_VALID_CASES)
def test_make_date_column_datetime_object_valid_input(
    input_df: pd.DataFrame, expected_df: pd.DataFrame
) -> None:
    _verify_expected_df_date_column_data(expected_df)

    # Copy to prevent modification if input_df
    test_df = input_df.copy()

    make_date_column_datetime_object(test_df)

    assert_frame_equal(test_df, expected_df)


@pytest.mark.parametrize("input_df, expected_msg, error_type", TEST_INVALID_CASES)
def test_make_date_column_datetime_object_invalid_input(
    input_df: pd.DataFrame, expected_msg: str, error_type: Type
) -> None:
    with pytest.raises(error_type) as err:
        make_date_column_datetime_object(input_df)
    assert str(err.value) == expected_msg
