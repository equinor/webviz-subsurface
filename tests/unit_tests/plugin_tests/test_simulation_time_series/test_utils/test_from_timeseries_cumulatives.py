from datetime import datetime
import pytest

import pandas as pd
from pandas._testing import assert_frame_equal

from webviz_subsurface._providers import Frequency
from webviz_subsurface.plugins._simulation_time_series.utils.from_timeseries_cumulatives import (
    calculate_from_resampled_cumulative_vectors_df,
    datetime_to_intervalstr,
    get_cumulative_vector_name,
    is_interval_or_average_vector,
    rename_vector_from_cumulative,
)

# fmt: off
# Monthly frequency - rate per day implies divide on days in month
TEST_INPUT_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime(2021, 1, 1),  1, 50.0,   250.0 ],
        [datetime(2021, 1, 8),  1, 100.0,  500.0 ],
        [datetime(2021, 1, 15), 1, 150.0,  750.0 ],
        [datetime(2021, 1, 22), 1, 200.0,  1000.0],
        [datetime(2021, 1, 29), 1, 250.0,  1250.0],
        [datetime(2021, 1, 1),  2, 300.0,  350.0 ],
        [datetime(2021, 1, 8),  2, 400.0,  700.0 ],
        [datetime(2021, 1, 15), 2, 500.0,  1050.0],
        [datetime(2021, 1, 22), 2, 600.0,  1400.0],
        [datetime(2021, 1, 29), 2, 700.0,  1750.0],
        [datetime(2021, 1, 1),  4, 1000.0, 450.0 ],
        [datetime(2021, 1, 8),  4, 1200.0, 900.0 ],
        [datetime(2021, 1, 15), 4, 1400.0, 1350.0],
        [datetime(2021, 1, 22), 4, 1600.0, 1800.0],
        [datetime(2021, 1, 29), 4, 1800.0, 2250.0],
    ],
)
TEST_INTVL_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "INTVL_A", "INTVL_B"],
    data=[
        [datetime(2021, 1, 1),  1, 50.0,  250.0],
        [datetime(2021, 1, 8),  1, 50.0,  250.0],
        [datetime(2021, 1, 15), 1, 50.0,  250.0],
        [datetime(2021, 1, 22), 1, 50.0,  250.0],
        [datetime(2021, 1, 29), 1, 0.0,   0.0  ],
        [datetime(2021, 1, 1),  2, 100.0, 350.0],
        [datetime(2021, 1, 8),  2, 100.0, 350.0],
        [datetime(2021, 1, 15), 2, 100.0, 350.0],
        [datetime(2021, 1, 22), 2, 100.0, 350.0],
        [datetime(2021, 1, 29), 2, 0.0,   0.0  ],
        [datetime(2021, 1, 1),  4, 200.0, 450.0],
        [datetime(2021, 1, 8),  4, 200.0, 450.0],
        [datetime(2021, 1, 15), 4, 200.0, 450.0],
        [datetime(2021, 1, 22), 4, 200.0, 450.0],
        [datetime(2021, 1, 29), 4, 0.0,   0.0  ],
    ],
)
TEST_AVG_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "AVG_A", "AVG_B"],
    data=[
        [datetime(2021, 1, 1),  1, 50.0/7.0,  250.0/7.0],
        [datetime(2021, 1, 8),  1, 50.0/7.0,  250.0/7.0],
        [datetime(2021, 1, 15), 1, 50.0/7.0,  250.0/7.0],
        [datetime(2021, 1, 22), 1, 50.0/7.0,  250.0/7.0],
        [datetime(2021, 1, 29), 1, 0.0,       0.0  ],
        [datetime(2021, 1, 1),  2, 100.0/7.0, 350.0/7.0],
        [datetime(2021, 1, 8),  2, 100.0/7.0, 350.0/7.0],
        [datetime(2021, 1, 15), 2, 100.0/7.0, 350.0/7.0],
        [datetime(2021, 1, 22), 2, 100.0/7.0, 350.0/7.0],
        [datetime(2021, 1, 29), 2, 0.0,       0.0  ],
        [datetime(2021, 1, 1),  4, 200.0/7.0, 450.0/7.0],
        [datetime(2021, 1, 8),  4, 200.0/7.0, 450.0/7.0],
        [datetime(2021, 1, 15), 4, 200.0/7.0, 450.0/7.0],
        [datetime(2021, 1, 22), 4, 200.0/7.0, 450.0/7.0],
        [datetime(2021, 1, 29), 4, 0.0,       0.0  ],
    ],
)
TEST_INPUT_WEEKLY_DF["DATE"] = pd.Series(TEST_INPUT_WEEKLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_INTVL_WEEKLY_DF["DATE"] = pd.Series(TEST_INTVL_WEEKLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_AVG_WEEKLY_DF["DATE"] = pd.Series(TEST_AVG_WEEKLY_DF["DATE"].dt.to_pydatetime(), dtype=object)

# Monthly frequency - rate per day implies divide on days in month
TEST_INPUT_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0,   250.0 ],
        [datetime(2021, 2, 1), 1, 100.0,  500.0 ],
        [datetime(2021, 3, 1), 1, 150.0,  750.0 ],
        [datetime(2021, 4, 1), 1, 200.0,  1000.0],
        [datetime(2021, 5, 1), 1, 250.0,  1250.0],
        [datetime(2021, 1, 1), 2, 300.0,  350.0 ],
        [datetime(2021, 2, 1), 2, 400.0,  700.0 ],
        [datetime(2021, 3, 1), 2, 500.0,  1050.0],
        [datetime(2021, 4, 1), 2, 600.0,  1400.0],
        [datetime(2021, 5, 1), 2, 700.0,  1750.0],
        [datetime(2021, 1, 1), 4, 1000.0, 450.0 ],
        [datetime(2021, 2, 1), 4, 1200.0, 900.0 ],
        [datetime(2021, 3, 1), 4, 1400.0, 1350.0],
        [datetime(2021, 4, 1), 4, 1600.0, 1800.0],
        [datetime(2021, 5, 1), 4, 1800.0, 2250.0],
    ],
)
TEST_INTVL_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "INTVL_A", "INTVL_B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0,  250.0],
        [datetime(2021, 2, 1), 1, 50.0,  250.0],
        [datetime(2021, 3, 1), 1, 50.0,  250.0],
        [datetime(2021, 4, 1), 1, 50.0,  250.0],
        [datetime(2021, 5, 1), 1, 0.0,   0.0  ],
        [datetime(2021, 1, 1), 2, 100.0, 350.0],
        [datetime(2021, 2, 1), 2, 100.0, 350.0],
        [datetime(2021, 3, 1), 2, 100.0, 350.0],
        [datetime(2021, 4, 1), 2, 100.0, 350.0],
        [datetime(2021, 5, 1), 2, 0.0,   0.0  ],
        [datetime(2021, 1, 1), 4, 200.0, 450.0],
        [datetime(2021, 2, 1), 4, 200.0, 450.0],
        [datetime(2021, 3, 1), 4, 200.0, 450.0],
        [datetime(2021, 4, 1), 4, 200.0, 450.0],
        [datetime(2021, 5, 1), 4, 0.0,   0.0  ],
    ],
)
TEST_AVG_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "AVG_A", "AVG_B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0/31.0,  250.0/31.0],
        [datetime(2021, 2, 1), 1, 50.0/28.0,  250.0/28.0],
        [datetime(2021, 3, 1), 1, 50.0/31.0,  250.0/31.0],
        [datetime(2021, 4, 1), 1, 50.0/30.0,  250.0/30.0],
        [datetime(2021, 5, 1), 1, 0.0,        0.0       ],
        [datetime(2021, 1, 1), 2, 100.0/31.0, 350.0/31.0],
        [datetime(2021, 2, 1), 2, 100.0/28.0, 350.0/28.0],
        [datetime(2021, 3, 1), 2, 100.0/31.0, 350.0/31.0],
        [datetime(2021, 4, 1), 2, 100.0/30.0, 350.0/30.0],
        [datetime(2021, 5, 1), 2, 0.0,        0.0       ],
        [datetime(2021, 1, 1), 4, 200.0/31.0, 450.0/31.0],
        [datetime(2021, 2, 1), 4, 200.0/28.0, 450.0/28.0],
        [datetime(2021, 3, 1), 4, 200.0/31.0, 450.0/31.0],
        [datetime(2021, 4, 1), 4, 200.0/30.0, 450.0/30.0],
        [datetime(2021, 5, 1), 4, 0.0,        0.0       ],
    ],
)
TEST_INPUT_MONTHLY_DF["DATE"] = pd.Series(TEST_INPUT_MONTHLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_INTVL_MONTHLY_DF["DATE"] = pd.Series(TEST_INTVL_MONTHLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_AVG_MONTHLY_DF["DATE"] = pd.Series(TEST_AVG_MONTHLY_DF["DATE"].dt.to_pydatetime(), dtype=object)

# Yearly frequency - rate per day implies divide on days in year
TEST_INPUT_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0,   250.0 ],
        [datetime(2021, 2, 1), 1, 100.0,  500.0 ],
        [datetime(2021, 3, 1), 1, 150.0,  750.0 ],
        [datetime(2021, 4, 1), 1, 200.0,  1000.0],
        [datetime(2021, 5, 1), 1, 250.0,  1250.0],
        [datetime(2021, 1, 1), 2, 300.0,  350.0 ],
        [datetime(2021, 2, 1), 2, 400.0,  700.0 ],
        [datetime(2021, 3, 1), 2, 500.0,  1050.0],
        [datetime(2021, 4, 1), 2, 600.0,  1400.0],
        [datetime(2021, 5, 1), 2, 700.0,  1750.0],
        [datetime(2021, 1, 1), 4, 1000.0, 450.0 ],
        [datetime(2021, 2, 1), 4, 1200.0, 900.0 ],
        [datetime(2021, 3, 1), 4, 1400.0, 1350.0],
        [datetime(2021, 4, 1), 4, 1600.0, 1800.0],
        [datetime(2021, 5, 1), 4, 1800.0, 2250.0],
    ],
)
TEST_INTVL_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "INTVL_A", "INTVL_B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0,  250.0],
        [datetime(2021, 2, 1), 1, 50.0,  250.0],
        [datetime(2021, 3, 1), 1, 50.0,  250.0],
        [datetime(2021, 4, 1), 1, 50.0,  250.0],
        [datetime(2021, 5, 1), 1, 0.0,   0.0  ],
        [datetime(2021, 1, 1), 2, 100.0, 350.0],
        [datetime(2021, 2, 1), 2, 100.0, 350.0],
        [datetime(2021, 3, 1), 2, 100.0, 350.0],
        [datetime(2021, 4, 1), 2, 100.0, 350.0],
        [datetime(2021, 5, 1), 2, 0.0,   0.0  ],
        [datetime(2021, 1, 1), 4, 200.0, 450.0],
        [datetime(2021, 2, 1), 4, 200.0, 450.0],
        [datetime(2021, 3, 1), 4, 200.0, 450.0],
        [datetime(2021, 4, 1), 4, 200.0, 450.0],
        [datetime(2021, 5, 1), 4, 0.0,   0.0  ],
    ],
)
TEST_AVG_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "AVG_A", "AVG_B"],
    data=[
        [datetime(2021, 1, 1), 1, 50.0/31.0,  250.0/31.0],
        [datetime(2021, 2, 1), 1, 50.0/28.0,  250.0/28.0],
        [datetime(2021, 3, 1), 1, 50.0/31.0,  250.0/31.0],
        [datetime(2021, 4, 1), 1, 50.0/30.0,  250.0/30.0],
        [datetime(2021, 5, 1), 1, 0.0,        0.0       ],
        [datetime(2021, 1, 1), 2, 100.0/31.0, 350.0/31.0],
        [datetime(2021, 2, 1), 2, 100.0/28.0, 350.0/28.0],
        [datetime(2021, 3, 1), 2, 100.0/31.0, 350.0/31.0],
        [datetime(2021, 4, 1), 2, 100.0/30.0, 350.0/30.0],
        [datetime(2021, 5, 1), 2, 0.0,        0.0       ],
        [datetime(2021, 1, 1), 4, 200.0/31.0, 450.0/31.0],
        [datetime(2021, 2, 1), 4, 200.0/28.0, 450.0/28.0],
        [datetime(2021, 3, 1), 4, 200.0/31.0, 450.0/31.0],
        [datetime(2021, 4, 1), 4, 200.0/30.0, 450.0/30.0],
        [datetime(2021, 5, 1), 4, 0.0,        0.0       ],
    ],
)
TEST_INPUT_YEARLY_DF["DATE"] = pd.Series(TEST_INPUT_YEARLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_INTVL_YEARLY_DF["DATE"] = pd.Series(TEST_INTVL_YEARLY_DF["DATE"].dt.to_pydatetime(), dtype=object)
TEST_AVG_YEARLY_DF["DATE"] = pd.Series(TEST_AVG_YEARLY_DF["DATE"].dt.to_pydatetime(), dtype=object)

# fmt: on

TEST_CASES = [
    pytest.param(TEST_INPUT_WEEKLY_DF, TEST_INTVL_WEEKLY_DF, TEST_AVG_WEEKLY_DF),
    pytest.param(TEST_INPUT_MONTHLY_DF, TEST_INTVL_MONTHLY_DF, TEST_AVG_MONTHLY_DF),
    pytest.param(TEST_INPUT_YEARLY_DF, TEST_INTVL_YEARLY_DF, TEST_AVG_YEARLY_DF),
]


@pytest.mark.parametrize("input_df, expected_intvl_df, expected_avg_df", TEST_CASES)
def test_calculate_from_resampled_cumulative_vectors_df(
    input_df: pd.DataFrame,
    expected_intvl_df: pd.DataFrame,
    expected_avg_df: pd.DataFrame,
) -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # INTVL_ due to as_rate_per_day = False
    calculated_intvl_df = calculate_from_resampled_cumulative_vectors_df(
        input_df, False
    )

    # AVG_ due to as_rate_per_day = True
    calculated_avg_df = calculate_from_resampled_cumulative_vectors_df(input_df, True)

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    calculated_intvl_df["DATE"] = pd.Series(
        calculated_intvl_df["DATE"].dt.to_pydatetime(), dtype=object
    )
    calculated_avg_df["DATE"] = pd.Series(
        calculated_avg_df["DATE"].dt.to_pydatetime(), dtype=object
    )

    assert_frame_equal(
        expected_intvl_df.sort_index(axis=1), calculated_intvl_df.sort_index(axis=1)
    )
    assert_frame_equal(
        expected_avg_df.sort_index(axis=1), calculated_avg_df.sort_index(axis=1)
    )


def test_is_interval_or_average_vector() -> None:
    assert is_interval_or_average_vector("AVG_Vector")
    assert is_interval_or_average_vector("INTVL_Vector")
    assert not is_interval_or_average_vector("avg_Vector")
    assert not is_interval_or_average_vector("intvl_Vector")
    assert not is_interval_or_average_vector("vector")


def test_get_cumulative_vector_name() -> None:
    assert "FOPT" == get_cumulative_vector_name("AVG_FOPT")
    assert "FOPT" == get_cumulative_vector_name("INTVL_FOPT")

    assert "FOPT" == get_cumulative_vector_name("AVG_FOPR")
    assert "FOPR" == get_cumulative_vector_name("INTVL_FOPR")

    # Expect ValueError when verifying vector not starting with "AVG_" or "INTVL_"
    try:
        get_cumulative_vector_name("Test_vector")
        pytest.fail('Expected retrieving of cumulative vector name for "Test_vector"')
    except ValueError as err:
        assert (
            f"{err}"
            == 'Expected "Test_vector" to be a vector calculated from cumulative!'
        )


def test_rename_vector_from_cumulative() -> None:
    assert "AVG_Vector" == rename_vector_from_cumulative("Vector", True)
    assert "AVG_FOPR" == rename_vector_from_cumulative("FOPT", True)
    assert "AVG_FOPS" == rename_vector_from_cumulative("FOPS", True)
    assert "INTVL_Vector" == rename_vector_from_cumulative("Vector", False)
    assert "INTVL_FOPT" == rename_vector_from_cumulative("FOPT", False)


def test_datetime_to_intervalstr() -> None:
    # Verify early return (ignore mypy)
    assert None is datetime_to_intervalstr(None, Frequency.WEEKLY)  # type: ignore

    test_date = datetime(2021, 11, 12, 13, 37)
    assert "2021-11-12" == datetime_to_intervalstr(test_date, Frequency.DAILY)
    assert "2021-W45" == datetime_to_intervalstr(test_date, Frequency.WEEKLY)
    assert "2021-11" == datetime_to_intervalstr(test_date, Frequency.MONTHLY)
    assert "2021-Q4" == datetime_to_intervalstr(test_date, Frequency.QUARTERLY)
    assert "2021" == datetime_to_intervalstr(test_date, Frequency.YEARLY)

    # Verify invalid frequency - i.e. isoformat!
    assert "2021-11-12T13:37:00" == datetime_to_intervalstr(test_date, None)  # type: ignore
