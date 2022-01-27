import datetime

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object
from webviz_subsurface.plugins._simulation_time_series.utils.from_timeseries_cumulatives import (
    calculate_from_resampled_cumulative_vectors_df,
    create_per_day_vector_name,
    create_per_interval_vector_name,
    datetime_to_intervalstr,
    get_cumulative_vector_name,
    is_per_interval_or_per_day_vector,
)

# *******************************************************************
#####################################################################
#
# CONFIGURE TESTDATA
#
#####################################################################
# *******************************************************************

# fmt: off
# Monthly frequency - rate per day implies divide on days in month
INPUT_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime.datetime(2021, 1, 1),  1, 50.0,   250.0 ],
        [datetime.datetime(2021, 1, 8),  1, 100.0,  500.0 ],
        [datetime.datetime(2021, 1, 15), 1, 150.0,  750.0 ],
        [datetime.datetime(2021, 1, 1),  2, 300.0,  350.0 ],
        [datetime.datetime(2021, 1, 8),  2, 400.0,  700.0 ],
        [datetime.datetime(2021, 1, 15), 2, 500.0,  1050.0],
        [datetime.datetime(2021, 1, 1),  4, 1000.0, 450.0 ],
        [datetime.datetime(2021, 1, 8),  4, 1200.0, 900.0 ],
        [datetime.datetime(2021, 1, 15), 4, 1400.0, 1350.0],
    ],
)
EXPECTED_PER_INTVL_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_INTVL_A", "PER_INTVL_B"],
    data=[
        [datetime.datetime(2021, 1, 1),  1, 50.0,  250.0],
        [datetime.datetime(2021, 1, 8),  1, 50.0,  250.0],
        [datetime.datetime(2021, 1, 15), 1, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1),  2, 100.0, 350.0],
        [datetime.datetime(2021, 1, 8),  2, 100.0, 350.0],
        [datetime.datetime(2021, 1, 15), 2, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1),  4, 200.0, 450.0],
        [datetime.datetime(2021, 1, 8),  4, 200.0, 450.0],
        [datetime.datetime(2021, 1, 15), 4, 0.0,   0.0  ],
    ],
)
EXPECTED_PER_DAY_WEEKLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_DAY_A", "PER_DAY_B"],
    data=[
        [datetime.datetime(2021, 1, 1),  1, 50.0/7.0,  250.0/7.0],
        [datetime.datetime(2021, 1, 8),  1, 50.0/7.0,  250.0/7.0],
        [datetime.datetime(2021, 1, 15), 1, 0.0,       0.0      ],
        [datetime.datetime(2021, 1, 1),  2, 100.0/7.0, 350.0/7.0],
        [datetime.datetime(2021, 1, 8),  2, 100.0/7.0, 350.0/7.0],
        [datetime.datetime(2021, 1, 15), 2, 0.0,       0.0      ],
        [datetime.datetime(2021, 1, 1),  4, 200.0/7.0, 450.0/7.0],
        [datetime.datetime(2021, 1, 8),  4, 200.0/7.0, 450.0/7.0],
        [datetime.datetime(2021, 1, 15), 4, 0.0,       0.0      ],
    ],
)
# Convert date columns to datetime.datetime
make_date_column_datetime_object(INPUT_WEEKLY_DF)
make_date_column_datetime_object(EXPECTED_PER_INTVL_WEEKLY_DF)
make_date_column_datetime_object(EXPECTED_PER_DAY_WEEKLY_DF)

# Monthly frequency - rate per day implies divide on days in month
INPUT_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0,   250.0 ],
        [datetime.datetime(2021, 2, 1), 1, 100.0,  500.0 ],
        [datetime.datetime(2021, 3, 1), 1, 150.0,  750.0 ],
        [datetime.datetime(2021, 1, 1), 2, 300.0,  350.0 ],
        [datetime.datetime(2021, 2, 1), 2, 400.0,  700.0 ],
        [datetime.datetime(2021, 3, 1), 2, 500.0,  1050.0],
        [datetime.datetime(2021, 1, 1), 4, 1000.0, 450.0 ],
        [datetime.datetime(2021, 2, 1), 4, 1200.0, 900.0 ],
        [datetime.datetime(2021, 3, 1), 4, 1400.0, 1350.0],
    ],
)
EXPECTED_PER_INTVL_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_INTVL_A", "PER_INTVL_B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0,  250.0],
        [datetime.datetime(2021, 2, 1), 1, 50.0,  250.0],
        [datetime.datetime(2021, 3, 1), 1, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1), 2, 100.0, 350.0],
        [datetime.datetime(2021, 2, 1), 2, 100.0, 350.0],
        [datetime.datetime(2021, 3, 1), 2, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1), 4, 200.0, 450.0],
        [datetime.datetime(2021, 2, 1), 4, 200.0, 450.0],
        [datetime.datetime(2021, 3, 1), 4, 0.0,   0.0  ],
    ],
)
EXPECTED_PER_DAY_MONTHLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_DAY_A", "PER_DAY_B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0/31.0,  250.0/31.0],
        [datetime.datetime(2021, 2, 1), 1, 50.0/28.0,  250.0/28.0],
        [datetime.datetime(2021, 3, 1), 1, 0.0,        0.0       ],
        [datetime.datetime(2021, 1, 1), 2, 100.0/31.0, 350.0/31.0],
        [datetime.datetime(2021, 2, 1), 2, 100.0/28.0, 350.0/28.0],
        [datetime.datetime(2021, 3, 1), 2, 0.0,        0.0       ],
        [datetime.datetime(2021, 1, 1), 4, 200.0/31.0, 450.0/31.0],
        [datetime.datetime(2021, 2, 1), 4, 200.0/28.0, 450.0/28.0],
        [datetime.datetime(2021, 3, 1), 4, 0.0,        0.0       ],
    ],
)
# Convert date columns to datetime.datetime
make_date_column_datetime_object(INPUT_MONTHLY_DF)
make_date_column_datetime_object(EXPECTED_PER_INTVL_MONTHLY_DF)
make_date_column_datetime_object(EXPECTED_PER_DAY_MONTHLY_DF)

# Yearly frequency - rate per day implies divide on days in year
INPUT_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "A", "B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0,   250.0 ],
        [datetime.datetime(2022, 1, 1), 1, 100.0,  500.0 ],
        [datetime.datetime(2023, 1, 1), 1, 150.0,  750.0 ],
        [datetime.datetime(2021, 1, 1), 2, 300.0,  350.0 ],
        [datetime.datetime(2022, 1, 1), 2, 400.0,  700.0 ],
        [datetime.datetime(2023, 1, 1), 2, 500.0,  1050.0],
        [datetime.datetime(2021, 1, 1), 4, 1000.0, 450.0 ],
        [datetime.datetime(2022, 1, 1), 4, 1200.0, 900.0 ],
        [datetime.datetime(2023, 1, 1), 4, 1400.0, 1350.0],
    ],
)
EXPECTED_PER_INTVL_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_INTVL_A", "PER_INTVL_B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0,  250.0],
        [datetime.datetime(2022, 1, 1), 1, 50.0,  250.0],
        [datetime.datetime(2023, 1, 1), 1, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1), 2, 100.0, 350.0],
        [datetime.datetime(2022, 1, 1), 2, 100.0, 350.0],
        [datetime.datetime(2023, 1, 1), 2, 0.0,   0.0  ],
        [datetime.datetime(2021, 1, 1), 4, 200.0, 450.0],
        [datetime.datetime(2022, 1, 1), 4, 200.0, 450.0],
        [datetime.datetime(2023, 1, 1), 4, 0.0,   0.0  ],
    ],
)
EXPECTED_PER_DAY_YEARLY_DF = pd.DataFrame(
    columns=["DATE", "REAL", "PER_DAY_A", "PER_DAY_B"],
    data=[
        [datetime.datetime(2021, 1, 1), 1, 50.0/365.0,  250.0/365.0],
        [datetime.datetime(2022, 1, 1), 1, 50.0/365.0,  250.0/365.0],
        [datetime.datetime(2023, 1, 1), 1, 0.0,         0.0        ],
        [datetime.datetime(2021, 1, 1), 2, 100.0/365.0, 350.0/365.0],
        [datetime.datetime(2022, 1, 1), 2, 100.0/365.0, 350.0/365.0],
        [datetime.datetime(2023, 1, 1), 2, 0.0,         0.0        ],
        [datetime.datetime(2021, 1, 1), 4, 200.0/365.0, 450.0/365.0],
        [datetime.datetime(2022, 1, 1), 4, 200.0/365.0, 450.0/365.0],
        [datetime.datetime(2023, 1, 1), 4, 0.0,         0.0        ],
    ],
)
# Convert date columns to datetime.datetime
make_date_column_datetime_object(INPUT_YEARLY_DF)
make_date_column_datetime_object(EXPECTED_PER_INTVL_YEARLY_DF)
make_date_column_datetime_object(EXPECTED_PER_DAY_YEARLY_DF)


# Monthly frequency after year 2262 - rate per day implies divide on days in month
AFTER_2262_MONTHLY_DATES = pd.Series(
    [
        datetime.datetime(2265, 1, 1),
        datetime.datetime(2265, 2, 1),
        datetime.datetime(2265, 3, 1),
        datetime.datetime(2265, 1, 1),
        datetime.datetime(2265, 2, 1),
        datetime.datetime(2265, 3, 1),
        datetime.datetime(2265, 1, 1),
        datetime.datetime(2265, 2, 1),
        datetime.datetime(2265, 3, 1),
    ]
)
# NOTE: datetime.datetime after year 2262 is not converted to pd.Timestamp!
INPUT_MONTHLY_AFTER_2262_DF = INPUT_MONTHLY_DF.copy()
INPUT_MONTHLY_AFTER_2262_DF["DATE"] = AFTER_2262_MONTHLY_DATES
EXPECTED_PER_INTVL_MONTHLY_AFTER_2262_DF = EXPECTED_PER_INTVL_MONTHLY_DF.copy()
EXPECTED_PER_INTVL_MONTHLY_AFTER_2262_DF["DATE"] = AFTER_2262_MONTHLY_DATES
EXPECTED_PER_DAY_MONTHLY_AFTER_2262_DF = EXPECTED_PER_DAY_MONTHLY_DF.copy()
EXPECTED_PER_DAY_MONTHLY_AFTER_2262_DF["DATE"] = AFTER_2262_MONTHLY_DATES

# fmt: on


# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************

TEST_CASES = [
    pytest.param(
        INPUT_WEEKLY_DF, EXPECTED_PER_INTVL_WEEKLY_DF, EXPECTED_PER_DAY_WEEKLY_DF
    ),
    pytest.param(
        INPUT_MONTHLY_DF, EXPECTED_PER_INTVL_MONTHLY_DF, EXPECTED_PER_DAY_MONTHLY_DF
    ),
    pytest.param(
        INPUT_YEARLY_DF, EXPECTED_PER_INTVL_YEARLY_DF, EXPECTED_PER_DAY_YEARLY_DF
    ),
    pytest.param(
        INPUT_MONTHLY_AFTER_2262_DF,
        EXPECTED_PER_INTVL_MONTHLY_AFTER_2262_DF,
        EXPECTED_PER_DAY_MONTHLY_AFTER_2262_DF,
    ),
]


@pytest.mark.parametrize(
    "input_df, expected_per_intvl_df, expected_per_day_df", TEST_CASES
)
def test_calculate_from_resampled_cumulative_vectors_df(
    input_df: pd.DataFrame,
    expected_per_intvl_df: pd.DataFrame,
    expected_per_day_df: pd.DataFrame,
) -> None:
    # PER_INTVL_ due to as_rate_per_day = False
    calculated_per_intvl_df = calculate_from_resampled_cumulative_vectors_df(
        input_df, False
    )

    # PER_DAY_ due to as_rate_per_day = True
    calculated_per_day_df = calculate_from_resampled_cumulative_vectors_df(
        input_df, True
    )

    assert_frame_equal(expected_per_intvl_df, calculated_per_intvl_df)
    assert_frame_equal(expected_per_day_df, calculated_per_day_df)


def test_calculate_from_resampled_cumulative_vectors_df_invalid_input() -> None:
    """Test assert check assert_date_column_is_datetime_object() in
    webviz_subsurface._utils.dataframe_utils.py
    """
    # fmt: off
    input_df = pd.DataFrame(
        columns=["DATE", "REAL", "A", "B"],
        data=[
            [pd.Timestamp(2020, 1, 1), 1, 50.0,   250.0 ],
            [pd.Timestamp(2020, 2, 1), 1, 100.0,  500.0 ],
            [pd.Timestamp(2020, 3, 1), 1, 150.0,  750.0 ],
            [pd.Timestamp(2020, 4, 1), 1, 200.0,  1000.0],
            [pd.Timestamp(2020, 5, 1), 1, 250.0,  1250.0],
        ],
    )
    # fmt: on

    with pytest.raises(ValueError) as err:
        calculate_from_resampled_cumulative_vectors_df(input_df, True)
    assert (
        str(err.value)
        == '"DATE"-column in dataframe is not on datetime.datetime format!'
    )


def test_is_per_interval_or_per_day_vector() -> None:
    assert is_per_interval_or_per_day_vector("PER_DAY_Vector")
    assert is_per_interval_or_per_day_vector("PER_INTVL_Vector")
    assert not is_per_interval_or_per_day_vector("per_day_Vector")
    assert not is_per_interval_or_per_day_vector("per_intvl_Vector")
    assert not is_per_interval_or_per_day_vector("vector")


def test_get_cumulative_vector_name() -> None:
    assert get_cumulative_vector_name("PER_DAY_FOPT") == "FOPT"
    assert get_cumulative_vector_name("PER_INTVL_FOPT") == "FOPT"

    assert get_cumulative_vector_name("PER_DAY_FOPR") == "FOPR"
    assert get_cumulative_vector_name("PER_INTVL_FOPR") == "FOPR"

    # Expect ValueError when verifying vector not starting with "PER_DAY_" or "PER_INTVL_"
    try:
        get_cumulative_vector_name("Test_vector")
        pytest.fail('Expected retrieving of cumulative vector name for "Test_vector"')
    except ValueError as err:
        assert (
            f"{err}"
            == 'Expected "Test_vector" to be a vector calculated from cumulative!'
        )


def test_create_per_day_vector_name() -> None:
    assert create_per_day_vector_name("Vector") == "PER_DAY_Vector"
    assert create_per_day_vector_name("FOPT") == "PER_DAY_FOPT"
    assert create_per_day_vector_name("FOPS") == "PER_DAY_FOPS"


def test_create_per_interval_vector_name() -> None:
    assert create_per_interval_vector_name("Vector") == "PER_INTVL_Vector"
    assert create_per_interval_vector_name("FOPT") == "PER_INTVL_FOPT"
    assert create_per_interval_vector_name("FOPS") == "PER_INTVL_FOPS"


def test_datetime_to_intervalstr() -> None:
    # Verify early return (ignore mypy)
    assert datetime_to_intervalstr(None, Frequency.WEEKLY) is None  # type: ignore

    test_date = datetime.datetime(2021, 11, 12, 13, 37)
    assert datetime_to_intervalstr(test_date, Frequency.DAILY) == "2021-11-12"
    assert datetime_to_intervalstr(test_date, Frequency.WEEKLY) == "2021-W45"
    assert datetime_to_intervalstr(test_date, Frequency.MONTHLY) == "2021-11"
    assert datetime_to_intervalstr(test_date, Frequency.QUARTERLY) == "2021-Q4"
    assert datetime_to_intervalstr(test_date, Frequency.YEARLY) == "2021"

    # Verify invalid frequency - i.e. isoformat!
    assert datetime_to_intervalstr(test_date, None) == "2021-11-12T13:37:00"  # type: ignore
