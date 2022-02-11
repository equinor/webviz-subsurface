import datetime

import pandas as pd
from pandas._testing import assert_frame_equal

from webviz_subsurface.plugins._simulation_time_series.utils.dataframe_utils import (
    create_relative_to_date_df,
)


def test_create_relative_to_date_df_consistent_realization_for_all_dates() -> None:
    # All dates are represented across all realizations
    input_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime.datetime(2263, 1, 1), 1, 10.0, 130.0],
            [datetime.datetime(2263, 2, 1), 1, 45.0, 135.0],
            [datetime.datetime(2263, 3, 1), 1, 50.0, 140.0],
            [datetime.datetime(2263, 4, 1), 1, 55.0, 145.0],
            [datetime.datetime(2263, 1, 1), 2, 11.0, 150.0],
            [datetime.datetime(2263, 2, 1), 2, 65.0, 155.0],
            [datetime.datetime(2263, 3, 1), 2, 70.0, 160.0],
            [datetime.datetime(2263, 4, 1), 2, 75.0, 165.0],
            [datetime.datetime(2263, 1, 1), 3, 12.0, 170.0],
            [datetime.datetime(2263, 2, 1), 3, 85.0, 175.0],
            [datetime.datetime(2263, 3, 1), 3, 90.0, 180.0],
            [datetime.datetime(2263, 4, 1), 3, 95.0, 185.0],
        ],
    )
    expected_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime.datetime(2263, 1, 1), 1, 0.0, 0.0],
            [datetime.datetime(2263, 2, 1), 1, 35.0, 5.0],
            [datetime.datetime(2263, 3, 1), 1, 40.0, 10.0],
            [datetime.datetime(2263, 4, 1), 1, 45.0, 15.0],
            [datetime.datetime(2263, 1, 1), 2, 0.0, 0.0],
            [datetime.datetime(2263, 2, 1), 2, 54.0, 5.0],
            [datetime.datetime(2263, 3, 1), 2, 59.0, 10.0],
            [datetime.datetime(2263, 4, 1), 2, 64.0, 15.0],
            [datetime.datetime(2263, 1, 1), 3, 0.0, 0.0],
            [datetime.datetime(2263, 2, 1), 3, 73.0, 5.0],
            [datetime.datetime(2263, 3, 1), 3, 78.0, 10.0],
            [datetime.datetime(2263, 4, 1), 3, 83.0, 15.0],
        ],
    )

    assert_frame_equal(
        create_relative_to_date_df(input_df, datetime.datetime(2263, 1, 1)), expected_df
    )


def test_create_relative_to_date_df_relative_date_missing_a_realization() -> None:
    # Missing datetime.datetime(2263, 1, 1) for real = 3!
    input_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime.datetime(2263, 1, 1), 1, 10.0, 130.0],
            [datetime.datetime(2263, 2, 1), 1, 45.0, 135.0],
            [datetime.datetime(2263, 3, 1), 1, 50.0, 140.0],
            [datetime.datetime(2263, 4, 1), 1, 55.0, 145.0],
            [datetime.datetime(2263, 1, 1), 2, 11.0, 150.0],
            [datetime.datetime(2263, 2, 1), 2, 65.0, 155.0],
            [datetime.datetime(2263, 3, 1), 2, 70.0, 160.0],
            [datetime.datetime(2263, 4, 1), 2, 75.0, 165.0],
            [datetime.datetime(2263, 2, 1), 3, 85.0, 175.0],
            [datetime.datetime(2263, 3, 1), 3, 90.0, 180.0],
            [datetime.datetime(2263, 4, 1), 3, 95.0, 185.0],
        ],
    )
    expected_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime.datetime(2263, 1, 1), 1, 0.0, 0.0],
            [datetime.datetime(2263, 2, 1), 1, 35.0, 5.0],
            [datetime.datetime(2263, 3, 1), 1, 40.0, 10.0],
            [datetime.datetime(2263, 4, 1), 1, 45.0, 15.0],
            [datetime.datetime(2263, 1, 1), 2, 0.0, 0.0],
            [datetime.datetime(2263, 2, 1), 2, 54.0, 5.0],
            [datetime.datetime(2263, 3, 1), 2, 59.0, 10.0],
            [datetime.datetime(2263, 4, 1), 2, 64.0, 15.0],
        ],
    )

    assert_frame_equal(
        create_relative_to_date_df(input_df, datetime.datetime(2263, 1, 1)), expected_df
    )


def test_create_relative_to_date_df_relative_date_not_existing() -> None:
    # Missing datetime.datetime(2263, 5, 1)
    input_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime.datetime(2263, 1, 1), 1, 10.0, 130.0],
            [datetime.datetime(2263, 2, 1), 1, 45.0, 135.0],
            [datetime.datetime(2263, 3, 1), 1, 50.0, 140.0],
            [datetime.datetime(2263, 4, 1), 1, 55.0, 145.0],
            [datetime.datetime(2263, 1, 1), 2, 11.0, 150.0],
            [datetime.datetime(2263, 2, 1), 2, 65.0, 155.0],
            [datetime.datetime(2263, 3, 1), 2, 70.0, 160.0],
            [datetime.datetime(2263, 4, 1), 2, 75.0, 165.0],
            [datetime.datetime(2263, 1, 1), 3, 12.0, 170.0],
            [datetime.datetime(2263, 2, 1), 3, 85.0, 175.0],
            [datetime.datetime(2263, 3, 1), 3, 90.0, 180.0],
            [datetime.datetime(2263, 4, 1), 3, 95.0, 185.0],
        ],
    )

    # Ensure dtype for columns for df with no rows
    _columns = {
        name: pd.Series(dtype=input_df.dtypes[name]) for name in input_df.columns
    }
    expected_df = pd.DataFrame(_columns)

    assert_frame_equal(
        create_relative_to_date_df(input_df, datetime.datetime(2263, 5, 1)), expected_df
    )
