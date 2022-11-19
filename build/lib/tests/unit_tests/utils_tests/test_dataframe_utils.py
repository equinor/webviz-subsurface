import datetime

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
INPUT_TIMESTAMP_DATETIME_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [pd.Timestamp(2000, 1, 1),       1.0],  # pd.Timestamp detected in df["DATE"][0]
        [datetime.datetime(2263, 2, 15), 1.0],
    ],
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
INPUT_TIMESTAMP_YEAR_2020_DF = pd.DataFrame(
    columns=["DATE", "A"],
    data=[
        [pd.Timestamp(2020, 1, 15), 1.0],
        [pd.Timestamp(2020, 2, 15), 2.0],
        [pd.Timestamp(2020, 3, 15), 3.0],
    ],
)

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
# fmt: on

# *******************************************************
#########################################################
#
# TESTING OF: assert_date_column_is_datetime_object()
#
#########################################################
# *******************************************************


def test_assert_date_column_is_datetime_object_no_date_column_error() -> None:
    with pytest.raises(ValueError) as err:
        assert_date_column_is_datetime_object(INPUT_EMPTY_DF)
    assert str(err.value) == 'df does not contain column "DATE"'


def test_assert_date_column_is_datetime_object_timestamp_input_error() -> None:
    # fmt: off
    input_timestamp_df = pd.DataFrame(
        columns=["DATE", "A"],
        data=[
            [pd.Timestamp(2000, 1, 15), 1.0],
            [pd.Timestamp(2000, 2, 15), 1.0]],
    )
    # fmt: on
    with pytest.raises(ValueError) as err:
        assert_date_column_is_datetime_object(input_timestamp_df)
    assert (
        str(err.value)
        == '"DATE"-column in dataframe is not on datetime.datetime format!'
    )


def test_assert_date_column_is_datetime_object_timestamp_datetime_input_error() -> None:
    with pytest.raises(ValueError) as err:
        assert_date_column_is_datetime_object(INPUT_TIMESTAMP_DATETIME_DF)
    assert (
        str(err.value)
        == '"DATE"-column in dataframe is not on datetime.datetime format!'
    )


def test_assert_date_column_is_datetime_object_no_rows_df() -> None:
    try:
        assert_date_column_is_datetime_object(INPUT_NO_ROWS_DF)

    # pylint: disable = bare-except
    except:
        pytest.fail("Excpected no raise of ERROR!")


def test_assert_date_column_is_datetime_object_datetime_year_2020() -> None:
    try:
        assert_date_column_is_datetime_object(INPUT_DATETIME_YEAR_2020_DF)

    # pylint: disable = bare-except
    except:
        pytest.fail("Excpected no raise of ERROR!")


def test_assert_date_column_is_datetime_object_datetime_year_2263() -> None:
    try:
        assert_date_column_is_datetime_object(INPUT_DATETIME_YEAR_2263_DF)

    # pylint: disable = bare-except
    except:
        pytest.fail("Excpected no raise of ERROR!")


def test_assert_date_column_is_datetime_object_datetime_timestamp_df() -> None:
    # fmt: off
    input_datetime_timestamp_df = pd.DataFrame(
        data=[
            [datetime.datetime(2263, 2, 1), 1.0],
            [pd.Timestamp(2000, 1, 1),      1.0],  # pd.Timestamp NOT detected in df["DATE"][1]
        ],
        columns=["DATE", "A"],
    )
    # fmt: on
    try:
        assert_date_column_is_datetime_object(input_datetime_timestamp_df)

    # pylint: disable = bare-except
    except:
        pytest.fail("Excpected no raise of ERROR!")


def test_assert_date_column_is_datetime_object_datetime_inconsistent_index_df() -> None:
    """To verify iloc usage"""
    # fmt: off
    input_datetime_year_2263_inconsistent_index_df = pd.DataFrame(
        columns=["DATE", "A"],
        data=[
            [datetime.datetime(2263, 1, 15), 1.0],
            [datetime.datetime(2263, 2, 15), 2.0],
            [datetime.datetime(2263, 3, 15), 3.0],
        ],
        index = [2,5,9]
    )
    # fmt: on
    try:
        assert_date_column_is_datetime_object(
            input_datetime_year_2263_inconsistent_index_df
        )

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


def _verify_expected_df_date_column_data(df: pd.DataFrame) -> None:
    """Verify dataframe contains column named "DATE" and that
    each row in column is of type datetime.datetime.

    NOTE: Can be 0 rows
    """
    assert "DATE" in df.columns
    for row in df["DATE"]:
        # pylint: disable = unidiomatic-typecheck
        assert type(row) == datetime.datetime


def test_make_date_column_datetime_object_datetime_year_2020_df() -> None:
    _verify_expected_df_date_column_data(EXPECTED_YEAR_2020_DF)

    # Copy to prevent modification if input_df
    test_df = INPUT_DATETIME_YEAR_2020_DF.copy()

    make_date_column_datetime_object(test_df)

    assert_frame_equal(test_df, EXPECTED_YEAR_2020_DF)


def test_make_date_column_datetime_object_timestamp_year_2020_df() -> None:
    _verify_expected_df_date_column_data(EXPECTED_YEAR_2020_DF)

    # Copy to prevent modification if input_df
    test_df = INPUT_TIMESTAMP_YEAR_2020_DF.copy()

    make_date_column_datetime_object(test_df)

    assert_frame_equal(test_df, EXPECTED_YEAR_2020_DF)


def test_make_date_column_datetime_object_datetime_year_2263_df() -> None:
    _verify_expected_df_date_column_data(EXPECTED_YEAR_2263_DF)

    # Copy to prevent modification if input_df
    test_df = INPUT_DATETIME_YEAR_2263_DF.copy()

    make_date_column_datetime_object(test_df)

    assert_frame_equal(test_df, EXPECTED_YEAR_2263_DF)


def test_make_date_column_datetime_object_no_rows_df() -> None:
    # Copy to prevent modification if input_df
    test_df = INPUT_NO_ROWS_DF.copy()

    make_date_column_datetime_object(test_df)

    assert_frame_equal(test_df, INPUT_NO_ROWS_DF)


def test_make_date_column_datetime_object_input_empty_df() -> None:
    with pytest.raises(ValueError) as err:
        make_date_column_datetime_object(INPUT_EMPTY_DF)
    assert str(err.value) == 'df does not contain column "DATE"'


def test_make_date_column_datetime_object_input_timestamp_datetime_df() -> None:
    with pytest.raises(AttributeError) as err:
        make_date_column_datetime_object(INPUT_TIMESTAMP_DATETIME_DF)
    assert str(err.value) == "Can only use .dt accessor with datetimelike values"


def test_make_date_column_datetime_object_input_date_year_2020_df() -> None:
    # fmt: off
    input_date_year_2020_df = pd.DataFrame(
        columns=["DATE", "A"],
        data=[
            [datetime.date(2020, 1, 15), 1.0],
            [datetime.date(2020, 2, 15), 2.0],
            [datetime.date(2020, 3, 15), 3.0],
        ],
    )
    # fmt: on
    with pytest.raises(ValueError) as err:
        make_date_column_datetime_object(input_date_year_2020_df)
    assert str(err.value) == f'Column "DATE" of type {datetime.date} is not handled!'
