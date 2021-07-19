import numpy as np
import pyarrow as pa

from webviz_subsurface._providers.ensemble_summary_provider_resampling import (
    Frequency,
    generate_normalized_sample_dates,
    interpolate_backfill,
    sample_single_real_table_at_date_NAIVE_SLOW,
)


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


def test_generate_sample_dates_yearly() -> None:

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


def test_interpolate_backfill() -> None:

    xp = np.array([0, 2, 4, 6])
    yp = np.array([0, 20, 40, 60])

    x = np.array([0, 2, 4, 6])
    y = interpolate_backfill(x, xp, yp, -99, 99)
    assert (y == yp).all()

    x = np.array([-1, 1, 5, 7])
    expected_y = np.array([-99, 20, 60, 99])
    y = interpolate_backfill(x, xp, yp, -99, 99)
    assert (y == expected_y).all()

    x = np.array([-2, -1, 0, 3, 3, 6, 7, 8])
    expected_y = np.array([-99, -99, 0, 40, 40, 60, 99, 99])
    y = interpolate_backfill(x, xp, yp, -99, 99)
    assert (y == expected_y).all()


def test_sample_single_real_table_at_date() -> None:

    date_arr = pa.array(
        [
            np.datetime64("2020-01-01", "ms"),
            np.datetime64("2020-01-04", "ms"),
            np.datetime64("2020-01-06", "ms"),
        ]
    )

    data = [
        date_arr,
        pa.array(np.full(3, 1), type="int64"),
        pa.array([10, 40, 60], type="float32"),
        pa.array([1, 4, 6], type="float32"),
    ]

    schema = pa.schema(
        [
            pa.field("DATE", pa.timestamp("ms")),
            pa.field("REAL", pa.int64()),
            pa.field("T", pa.float32(), metadata={b"smry_meta": b'{"is_rate": false}'}),
            pa.field("R", pa.float32(), metadata={b"smry_meta": b'{"is_rate": true}'}),
        ]
    )

    table = pa.table(data, schema=schema)

    # Exact hit, first actual date
    sampledate = np.datetime64("2020-01-01", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 10
    assert res["R"][0].as_py() == 1

    # Exact hit, last actual date
    sampledate = np.datetime64("2020-01-06", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["R"][0].as_py() == 6

    # Exact hit, middle date
    sampledate = np.datetime64("2020-01-04", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 40
    assert res["R"][0].as_py() == 4

    # Before first date
    sampledate = np.datetime64("2019-01-01", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 10
    assert res["R"][0].as_py() == 0

    # After last date
    sampledate = np.datetime64("2020-01-10", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 60
    assert res["R"][0].as_py() == 0

    # Interpolated
    sampledate = np.datetime64("2020-01-02", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 20
    assert res["R"][0].as_py() == 4

    # Interpolated
    sampledate = np.datetime64("2020-01-03", "ms")
    res = sample_single_real_table_at_date_NAIVE_SLOW(table, sampledate)
    assert res.num_rows == 1
    assert res["DATE"].to_numpy()[0] == sampledate
    assert res["REAL"][0].as_py() == 1
    assert res["T"][0].as_py() == 30
    assert res["R"][0].as_py() == 4
