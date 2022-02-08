import datetime

import pytest

from webviz_subsurface.plugins._simulation_time_series.utils.datetime_utils import (
    from_str,
    to_str,
)


def test_from_str_success() -> None:
    assert from_str("2021-03-11") == datetime.datetime(2021, 3, 11)
    assert from_str("1956-08-26") == datetime.datetime(1956, 8, 26)


def test_from_str_assert() -> None:
    # Invalid datetime arguments (hour, minute, second, microsecond)
    invalid_dates = ["2021-03-11-23-55-11", "1996-05-26-23", "2001-08-11-11-43"]
    for _date in invalid_dates:
        with pytest.raises(ValueError) as err:
            from_str(_date)
        assert str(err.value) == f"unconverted data remains: {_date[10:]}"


def test_to_str_success() -> None:
    assert to_str(datetime.datetime(2021, 6, 13)) == "2021-06-13"
    assert to_str(datetime.datetime(2021, 12, 28)) == "2021-12-28"
    assert to_str(datetime.datetime(2021, 3, 7, 0)) == "2021-03-07"
    assert to_str(datetime.datetime(2021, 10, 22, 0, 0)) == "2021-10-22"
    assert to_str(datetime.datetime(2021, 1, 23, 0, 0, 0)) == "2021-01-23"
    assert to_str(datetime.datetime(2021, 12, 28, 0, 0, 0, 0)) == "2021-12-28"


def test_to_str_assert() -> None:
    # Invalid datetime arguments (hour, minute, second, microsecond)
    invalid_dates = [
        datetime.datetime(2021, 6, 13, 15, 32, 11, 43),
        datetime.datetime(2021, 6, 13, 5, 21, 45),
        datetime.datetime(2021, 6, 13, 23, 55),
        datetime.datetime(2021, 6, 13, 5),
    ]

    for _date in invalid_dates:
        with pytest.raises(ValueError) as err:
            to_str(_date)
        assert (
            str(err.value)
            == f"Invalid date resolution, expected no data for hour, minute, second"
            f" or microsecond for {str(_date)}"
        )
