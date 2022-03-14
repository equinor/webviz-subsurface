import numpy as np
import pyarrow as pa

from webviz_subsurface._providers.ensemble_summary_provider._resampling import (
    Frequency,
    calc_intersection_of_normalized_date_intervals,
    generate_normalized_sample_dates,
    get_normalized_min_max_sample_date,
    interpolate_backfill,
    sample_segmented_multi_real_table_at_date,
)


def _create_table_from_row_data(
    per_row_input_data: list, schema: pa.Schema
) -> pa.Table:
    # Turn rows into columns
    columns_with_header = list(zip(*per_row_input_data))

    input_dict = {}
    for col in columns_with_header:
        colname = col[0]
        coldata = col[1:]
        input_dict[colname] = coldata

    table = pa.Table.from_pydict(input_dict, schema=schema)

    return table


def test_generate_sample_dates_daily() -> None:

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-30"), np.datetime64("2021-01-05"), Frequency.DAILY
    )
    assert len(dates) == 7
    assert dates[0] == np.datetime64("2020-12-30")
    assert dates[-1] == np.datetime64("2021-01-05")

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-30T01:30"),
        np.datetime64("2021-01-05T02:30"),
        Frequency.DAILY,
    )
    assert len(dates) == 8
    assert dates[0] == np.datetime64("2020-12-30")
    assert dates[-1] == np.datetime64("2021-01-06")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-01-20"), np.datetime64("2020-01-20"), Frequency.DAILY
    )
    assert len(dates) == 1
    assert dates[0] == np.datetime64("2020-01-20")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-01-20T01:30"),
        np.datetime64("2020-01-20T01:30"),
        Frequency.DAILY,
    )
    assert len(dates) == 2
    assert dates[0] == np.datetime64("2020-01-20")
    assert dates[1] == np.datetime64("2020-01-21")


def test_generate_sample_dates_weekly() -> None:

    # Mondays
    #   2020-12-21
    #   2020-12-28
    #   2021-01-04
    #   2021-01-11

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-28"), np.datetime64("2021-01-11"), Frequency.WEEKLY
    )
    assert len(dates) == 3
    assert dates[0] == np.datetime64("2020-12-28")
    assert dates[-1] == np.datetime64("2021-01-11")

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-27T00:01"),
        np.datetime64("2021-01-05T02:30"),
        Frequency.WEEKLY,
    )
    assert len(dates) == 4
    assert dates[0] == np.datetime64("2020-12-21")
    assert dates[-1] == np.datetime64("2021-01-11")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-21"), np.datetime64("2020-12-21"), Frequency.WEEKLY
    )
    assert len(dates) == 1
    assert dates[0] == np.datetime64("2020-12-21")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-22"),
        np.datetime64("2020-12-22"),
        Frequency.WEEKLY,
    )
    assert len(dates) == 2
    assert dates[0] == np.datetime64("2020-12-21")
    assert dates[1] == np.datetime64("2020-12-28")


def test_generate_sample_dates_monthly() -> None:

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-01"), np.datetime64("2021-01-01"), Frequency.MONTHLY
    )
    assert len(dates) == 2
    assert dates[0] == np.datetime64("2020-12-01")
    assert dates[-1] == np.datetime64("2021-01-01")

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-30"),
        np.datetime64("2022-01-01T01:01"),
        Frequency.MONTHLY,
    )
    assert len(dates) == 15
    assert dates[0] == np.datetime64("2020-12-01")
    assert dates[-1] == np.datetime64("2022-02-01")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-01"), np.datetime64("2020-12-01"), Frequency.MONTHLY
    )
    assert len(dates) == 1
    assert dates[0] == np.datetime64("2020-12-01")


def test_generate_sample_dates_yearly() -> None:

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-01-01"), np.datetime64("2020-01-02"), Frequency.YEARLY
    )
    assert len(dates) == 2
    assert dates[0] == np.datetime64("2020-01-01")
    assert dates[-1] == np.datetime64("2021-01-01")

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-01-01"), np.datetime64("2022-01-01"), Frequency.YEARLY
    )
    assert len(dates) == 3
    assert dates[0] == np.datetime64("2020-01-01")
    assert dates[-1] == np.datetime64("2022-01-01")

    dates = generate_normalized_sample_dates(
        np.datetime64("2020-12-30"),
        np.datetime64("2022-01-01T01:01"),
        Frequency.YEARLY,
    )
    assert len(dates) == 4
    assert dates[0] == np.datetime64("2020-01-01")
    assert dates[-1] == np.datetime64("2023-01-01")

    # Same min and max raw date
    dates = generate_normalized_sample_dates(
        np.datetime64("2020-01-01"), np.datetime64("2020-01-01"), Frequency.YEARLY
    )
    assert len(dates) == 1
    assert dates[0] == np.datetime64("2020-01-01")


def test_get_normalized_min_max_sample_dates() -> None:

    # Daily
    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2020-12-30"), np.datetime64("2020-12-30"), Frequency.DAILY
    )
    assert min_date == np.datetime64("2020-12-30")
    assert max_date == np.datetime64("2020-12-30")

    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2020-12-30"), np.datetime64("2021-01-05"), Frequency.DAILY
    )
    assert min_date == np.datetime64("2020-12-30")
    assert max_date == np.datetime64("2021-01-05")

    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2020-12-30T01:30"),
        np.datetime64("2021-01-05T02:30"),
        Frequency.DAILY,
    )
    assert min_date == np.datetime64("2020-12-30")
    assert max_date == np.datetime64("2021-01-06")

    # Weekly
    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2020-12-20"),
        np.datetime64("2021-01-21"),
        Frequency.WEEKLY,
    )
    assert min_date == np.datetime64("2020-12-14")
    assert max_date == np.datetime64("2021-01-25")

    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2021-01-25"),
        np.datetime64("2021-01-26"),
        Frequency.WEEKLY,
    )
    assert min_date == np.datetime64("2021-01-25")
    assert max_date == np.datetime64("2021-02-01")

    # Monthly
    min_date, max_date = get_normalized_min_max_sample_date(
        np.datetime64("2021-02-01"),
        np.datetime64("2021-02-02"),
        Frequency.MONTHLY,
    )
    assert min_date == np.datetime64("2021-02-01")
    assert max_date == np.datetime64("2021-03-01")

    # TODO: Test for the rest of the frequencies
    # :


def test_find_normalized_intersection_of_date_intervals() -> None:
    intervals = [
        (np.datetime64("2020-01-20"), np.datetime64("2020-01-22")),
        (np.datetime64("2020-01-22"), np.datetime64("2020-01-29")),
    ]
    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.DAILY)
    assert isect is not None
    assert isect[0] == np.datetime64("2020-01-22")
    assert isect[1] == np.datetime64("2020-01-22")

    intervals = [
        (np.datetime64("2020-01-20"), np.datetime64("2020-01-22")),
        (np.datetime64("2029-01-31"), np.datetime64("2029-01-31")),
    ]
    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.DAILY)
    assert isect is None

    intervals = [
        (np.datetime64("2020-12-20"), np.datetime64("2021-01-21")),
        (np.datetime64("2021-02-01"), np.datetime64("2021-02-02")),
    ]
    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.DAILY)
    assert isect is None

    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.WEEKLY)
    assert isect is None

    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.MONTHLY)
    assert isect is not None
    assert isect[0] == np.datetime64("2021-02-01")
    assert isect[1] == np.datetime64("2021-02-01")

    isect = calc_intersection_of_normalized_date_intervals(intervals, Frequency.YEARLY)
    assert isect is not None
    assert isect[0] == np.datetime64("2021-01-01")
    assert isect[1] == np.datetime64("2022-01-01")


def test_interpolate_backfill() -> None:

    raw_x = np.array([0, 2, 4, 6])
    raw_y = np.array([0, 20, 40, 60])

    x = np.array([0, 2, 4, 6])
    y = interpolate_backfill(x, raw_x, raw_y, -99, 99)
    assert (y == raw_y).all()

    x = np.array([-1, 1, 5, 7])
    expected_y = np.array([-99, 20, 60, 99])
    y = interpolate_backfill(x, raw_x, raw_y, -99, 99)
    assert (y == expected_y).all()

    x = np.array([-2, -1, 0, 3, 3, 6, 7, 8])
    expected_y = np.array([-99, -99, 0, 40, 40, 60, 99, 99])
    y = interpolate_backfill(x, raw_x, raw_y, -99, 99)
    assert (y == expected_y).all()


def test_sample_segmented_multi_real_table_at_date_with_single_real() -> None:
    # pylint: disable=too-many-statements
    # fmt:off
    input_data = [
        ["DATE",                             "REAL",  "T",   "R"],
        [np.datetime64("2020-01-01", "ms"),  1,       10.0,  1],
        [np.datetime64("2020-01-04", "ms"),  1,       40.0,  4],
        [np.datetime64("2020-01-06", "ms"),  1,       60.0,  6],
    ]
    # fmt:on

    schema = pa.schema(
        [
            pa.field("DATE", pa.timestamp("ms")),
            pa.field("REAL", pa.int64()),
            pa.field("T", pa.float32(), metadata={b"is_rate": b"False"}),
            pa.field("R", pa.float32(), metadata={b"is_rate": b"True"}),
        ]
    )

    table = _create_table_from_row_data(per_row_input_data=input_data, schema=schema)

    # Exact hit, first actual date
    sampledate = np.datetime64("2020-01-01", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 10
    assert res["R"][0].as_py() == 1

    # Exact hit, last actual date
    sampledate = np.datetime64("2020-01-06", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["R"][0].as_py() == 6

    # Exact hit, middle date
    sampledate = np.datetime64("2020-01-04", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 40
    assert res["R"][0].as_py() == 4

    # Before first date
    sampledate = np.datetime64("2019-01-01", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 10
    assert res["R"][0].as_py() == 0

    # After last date
    sampledate = np.datetime64("2020-01-10", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["R"][0].as_py() == 0

    # Interpolated
    sampledate = np.datetime64("2020-01-02", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 20
    assert res["R"][0].as_py() == 4

    # Interpolated
    sampledate = np.datetime64("2020-01-03", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 30
    assert res["R"][0].as_py() == 4


def test_sample_segmented_multi_real_table_at_date() -> None:
    # pylint: disable=too-many-statements
    # fmt:off
    input_data = [
        ["DATE",                             "REAL",  "T",    "R"],
        [np.datetime64("2020-01-01", "ms"),  0,       10.0,   1],
        [np.datetime64("2020-01-04", "ms"),  0,       40.0,   4],
        [np.datetime64("2020-01-06", "ms"),  0,       60.0,   6],
        [np.datetime64("2020-01-02", "ms"),  1,       2000.0,  200],
        [np.datetime64("2020-01-05", "ms"),  1,       5000.0,  500],
        [np.datetime64("2020-01-07", "ms"),  1,       7000.0,  700],
    ]
    # fmt:on

    schema = pa.schema(
        [
            pa.field("DATE", pa.timestamp("ms")),
            pa.field("REAL", pa.int64()),
            pa.field("T", pa.float32(), metadata={b"is_rate": b"False"}),
            pa.field("R", pa.float32(), metadata={b"is_rate": b"True"}),
        ]
    )

    table = _create_table_from_row_data(per_row_input_data=input_data, schema=schema)

    # Exact hit on first date in R=0
    sampledate = np.datetime64("2020-01-01", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 10
    assert res["T"][1].as_py() == 2000
    assert res["R"][0].as_py() == 1
    assert res["R"][1].as_py() == 0

    # Exact hit on first date in R=1
    sampledate = np.datetime64("2020-01-02", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 20
    assert res["T"][1].as_py() == 2000
    assert res["R"][0].as_py() == 4
    assert res["R"][1].as_py() == 200

    # Exact hit on last actual date in R=0
    sampledate = np.datetime64("2020-01-06", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["T"][1].as_py() == 6000
    assert res["R"][0].as_py() == 6
    assert res["R"][1].as_py() == 700

    # Exact hit on last actual date in R=1
    sampledate = np.datetime64("2020-01-07", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["T"][1].as_py() == 7000
    assert res["R"][0].as_py() == 0
    assert res["R"][1].as_py() == 700

    # Interpolated
    sampledate = np.datetime64("2020-01-02", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 20
    assert res["T"][1].as_py() == 2000
    assert res["R"][0].as_py() == 4
    assert res["R"][1].as_py() == 200

    # Interpolated
    sampledate = np.datetime64("2020-01-03", "ms")
    res = sample_segmented_multi_real_table_at_date(table, sampledate)
    assert res.num_rows == 2
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["DATE"].to_numpy()[1] == sampledate
    assert res["REAL"][0].as_py() == 0
    assert res["REAL"][1].as_py() == 1
    assert res["T"][0].as_py() == 30
    assert res["T"][1].as_py() == 3000
    assert res["R"][0].as_py() == 4
    assert res["R"][1].as_py() == 500
