from datetime import datetime
import pytest

import pandas as pd

from webviz_subsurface._providers import Frequency
from webviz_subsurface.plugins._simulation_time_series.utils.from_timeseries_cumulatives import (
    calculate_from_resampled_cumulative_vectors_df,
    datetime_to_intervalstr,
    get_cumulative_vector_name,
    is_interval_or_average_vector,
    rename_vector_from_cumulative,
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


def test_calculate_from_resampled_cumulative_vectors_df_intvl_monthly() -> None:
    # TODO: Update test when decision on how to handle datetime.datetime -> pd.Timeseries
    # for "DATE" column when utilizing df.set_index(["DATE"]).

    # fmt: off
    input_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [datetime(2000, 1, 1), 1, 1.0,  50.0],
            [datetime(2000, 2, 1), 1, 3.0,  100.0],
            [datetime(2000, 3, 1), 1, 5.0,  150.0],
            [datetime(2000, 4, 1), 1, 7.0,  200.0],
            [datetime(2000, 5, 1), 1, 9.0,  250.0],
            [datetime(2000, 1, 1), 2, 10.0, 300.0],
            [datetime(2000, 2, 1), 2, 20.0, 400.0],
            [datetime(2000, 3, 1), 2, 30.0, 500.0],
            [datetime(2000, 4, 1), 2, 40.0, 600.0],
            [datetime(2000, 5, 1), 2, 50.0, 700.0],
            [datetime(2000, 1, 1), 4, 5.0,  1000.0],
            [datetime(2000, 2, 1), 4, 20.0, 1200.0],
            [datetime(2000, 3, 1), 4, 35.0, 1400.0],
            [datetime(2000, 4, 1), 4, 50.0, 1600.0],
            [datetime(2000, 5, 1), 4, 65.0, 1800.0],
        ],
    )
    input_df["DATE"] = pd.Series(input_df["DATE"].dt.to_pydatetime(), dtype=object)

    # Monthly frequency
    expected_df = pd.DataFrame(
        columns=["DATE", "REAL", "INTVL_A", "INTVL_B"],
        data=[
            [datetime(2000, 1, 1), 1, 2.0,  50.0 ],
            [datetime(2000, 2, 1), 1, 2.0,  50.0 ],
            [datetime(2000, 3, 1), 1, 2.0,  50.0 ],
            [datetime(2000, 4, 1), 1, 2.0,  50.0 ],
            [datetime(2000, 5, 1), 1, 0.0,  0.0  ],
            [datetime(2000, 1, 1), 2, 10.0, 100.0],
            [datetime(2000, 2, 1), 2, 10.0, 100.0],
            [datetime(2000, 3, 1), 2, 10.0, 100.0],
            [datetime(2000, 4, 1), 2, 10.0, 100.0],
            [datetime(2000, 5, 1), 2, 0.0,  0.0  ],
            [datetime(2000, 1, 1), 4, 15.0, 200.0],
            [datetime(2000, 2, 1), 4, 15.0, 200.0],
            [datetime(2000, 3, 1), 4, 15.0, 200.0],
            [datetime(2000, 4, 1), 4, 15.0, 200.0],
            [datetime(2000, 5, 1), 4, 0.0,  0.0  ],
        ],
    )
    expected_df["DATE"] = pd.Series(expected_df["DATE"].dt.to_pydatetime(), dtype=object)
    # fmt: on

    # INTVL_ due to as_rate_per_day = True
    calculated_df = calculate_from_resampled_cumulative_vectors_df(input_df, False)

    # TODO: Remove conversion when datetime.datetime -> pd.Timeseries for "DATE" column is resolved
    calculated_df["DATE"] = pd.Series(
        calculated_df["DATE"].dt.to_pydatetime(), dtype=object
    )

    assert expected_df.equals(calculated_df)
    assert expected_df.columns.equals(calculated_df.columns)
