import datetime

import pandas as pd

from pandas._testing import assert_frame_equal

from webviz_subsurface.plugins._simulation_time_series.utils.dataframe_utils import (
    create_relative_to_date_df_group_by_real,
    create_relative_to_date_df_group_by_real_2,
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

    first_method = create_relative_to_date_df_group_by_real(
        input_df, datetime.datetime(2263, 1, 1)
    )
    second_method = create_relative_to_date_df_group_by_real_2(
        input_df, datetime.datetime(2263, 1, 1)
    )

    assert_frame_equal(first_method, expected_df)
    assert_frame_equal(second_method, expected_df)
    assert False


def test_create_relative_to_date_df_relative_date_missing_realization() -> None:
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

    first_method = create_relative_to_date_df_group_by_real(
        input_df, datetime.datetime(2263, 1, 1)
    )
    second_method = create_relative_to_date_df_group_by_real_2(
        input_df, datetime.datetime(2263, 1, 1)
    )
    assert_frame_equal(first_method, expected_df)
    assert_frame_equal(second_method, expected_df)
    assert False
