from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from webviz_subsurface._providers.ensemble_summary_provider._provider_impl_arrow_lazy import (
    ProviderImplArrowLazy,
)
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    DateSpan,
    EnsembleSummaryProvider,
    Frequency,
    ResamplingOptions,
)


def _add_mock_smry_meta_to_table(table: pa.Table) -> pa.Table:
    schema = table.schema
    for colname in schema.names:
        is_rate = bool("_r" in colname)
        is_total = bool("_t" in colname)

        metadata = None
        if is_rate or is_total:
            metadata = {
                b"unit": b"N/A",
                b"is_rate": b"True" if is_rate else b"False",
                b"is_total": b"True" if is_total else b"False",
                b"is_historical": b"False",
                b"keyword": b"UNKNOWN",
            }

        if metadata:
            idx = schema.get_field_index(colname)
            field = schema.field(idx)
            field = field.with_metadata(metadata)
            schema = schema.set(idx, field)

    table = table.cast(schema)
    return table


def _split_into_per_realization_tables(table: pa.Table) -> Dict[int, pa.Table]:
    per_real_tables: Dict[int, pa.Table] = {}
    unique_reals = table.column("REAL").unique().to_pylist()
    for real in unique_reals:
        # pylint: disable=no-member
        mask = pc.is_in(table["REAL"], value_set=pa.array([real]))
        real_table = table.filter(mask).drop(["REAL"])
        per_real_tables[real] = real_table

    return per_real_tables


def _create_provider_obj_with_data(
    input_data: list,
    storage_dir: Path,
) -> EnsembleSummaryProvider:

    # Turn rows into columns
    columns_with_header = list(zip(*input_data))

    input_dict = {}
    for col in columns_with_header:
        colname = col[0]
        coldata = col[1:]
        input_dict[colname] = coldata
    input_table = pa.Table.from_pydict(input_dict)

    input_table = _add_mock_smry_meta_to_table(input_table)

    # Split into per realization tables
    per_real_tables = _split_into_per_realization_tables(input_table)

    ProviderImplArrowLazy.write_backing_store_from_per_realization_tables(
        storage_dir, "dummy_key", per_real_tables
    )
    new_provider = ProviderImplArrowLazy.from_backing_store(storage_dir, "dummy_key")

    if not new_provider:
        raise ValueError("Failed to create EnsembleSummaryProvider")

    return new_provider


def test_create_with_dates_after_2262(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                                 "REAL", "A"],
        [np.datetime64("2000-01-02T00:00", "ms"), 1,     10.0],
        [np.datetime64("2500-12-20T23:59", "ms"), 1,     12.0],
        [np.datetime64("2500-12-21T22:58", "ms"), 1,     13.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    dates = provider.dates(resampling_frequency=None)
    assert len(dates) == 3
    assert dates[0] == datetime(2000, 1, 2, 00, 00)
    assert dates[1] == datetime(2500, 12, 20, 23, 59)
    assert dates[2] == datetime(2500, 12, 21, 22, 58)


def test_get_vector_names(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",  "C",   "Z"],
        [np.datetime64("2023-12-20", "ms"),  0,      10.0,  1.0,  0.0 ],
        [np.datetime64("2023-12-20", "ms"),  1,      12.0,  1.0,  0.0 ],
        [np.datetime64("2023-12-21", "ms"),  1,      13.0,  1.0,  0.0 ],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_vecnames = provider.vector_names()
    assert len(all_vecnames) == 3
    assert all_vecnames == ["A", "C", "Z"]

    non_const_vec_names = provider.vector_names_filtered_by_value(
        exclude_constant_values=True
    )
    assert len(non_const_vec_names) == 1
    assert non_const_vec_names == ["A"]

    non_zero_vec_names = provider.vector_names_filtered_by_value(
        exclude_all_values_zero=True
    )
    assert len(non_zero_vec_names) == 2
    assert non_zero_vec_names == ["A", "C"]

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2


def test_get_dates_intersection_without_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A"],
        [np.datetime64("2020-12-10", "ms"),  1,      1.0],
        [np.datetime64("2020-12-20", "ms"),  1,      2.0],
        [np.datetime64("2020-12-10", "ms"),  2,      3.0],
        [np.datetime64("2020-12-15", "ms"),  2,      4.0],
        [np.datetime64("2020-12-20", "ms"),  2,      5.0],
        [np.datetime64("2099-12-01", "ms"),  9,      6.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_realizations = provider.realizations()
    assert len(all_realizations) == 3

    # Intersection accross all realizations is empty
    all_real_dates = provider.dates(None, DateSpan.INTERSECTION)
    assert len(all_real_dates) == 0

    r12_dates = provider.dates(None, DateSpan.INTERSECTION, [1, 2])
    assert len(r12_dates) == 2
    assert r12_dates == sorted(r12_dates)
    assert isinstance(r12_dates[0], datetime)

    r1_dates = provider.dates(None, DateSpan.INTERSECTION, [1])
    r2_dates = provider.dates(None, DateSpan.INTERSECTION, [2])
    assert len(r1_dates) == 2
    assert len(r2_dates) == 3
    assert r1_dates == sorted(r1_dates)
    assert r2_dates == sorted(r2_dates)


def test_get_dates_union_without_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A"],
        [np.datetime64("2020-12-15", "ms"),  1,      1.0],
        [np.datetime64("2020-12-10", "ms"),  2,      2.0],
        [np.datetime64("2020-12-20", "ms"),  2,      3.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2

    union_of_dates = provider.dates(None, DateSpan.UNION)
    assert len(union_of_dates) == 3
    assert union_of_dates == sorted(union_of_dates)

    r1_dates = provider.dates(None, DateSpan.UNION, [1])
    r2_dates = provider.dates(None, DateSpan.UNION, [2])
    assert len(r1_dates) == 1
    assert len(r2_dates) == 2
    assert r1_dates == sorted(r1_dates)
    assert r2_dates == sorted(r2_dates)


def test_get_dates_union_with_daily_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",],
        [np.datetime64("2020-01-01", "ms"),  0,      10.0],
        [np.datetime64("2020-01-04", "ms"),  0,      40.0],
        [np.datetime64("2020-01-06", "ms"),  1,      60.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2

    union_dates = provider.dates(Frequency.DAILY, DateSpan.UNION)
    assert len(union_dates) == 6
    assert isinstance(union_dates[0], datetime)
    assert union_dates[0] == datetime(2020, 1, 1)
    assert union_dates[1] == datetime(2020, 1, 2)
    assert union_dates[2] == datetime(2020, 1, 3)
    assert union_dates[3] == datetime(2020, 1, 4)
    assert union_dates[4] == datetime(2020, 1, 5)
    assert union_dates[5] == datetime(2020, 1, 6)

    r0_dates = provider.dates(Frequency.DAILY, DateSpan.UNION, realizations=[0])
    assert len(r0_dates) == 4

    r1_dates = provider.dates(Frequency.DAILY, DateSpan.UNION, realizations=[1])
    assert len(r1_dates) == 1


def test_get_dates_intersection_with_daily_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",],
        [np.datetime64("2020-01-01", "ms"),  0,      10.0],
        [np.datetime64("2020-01-05", "ms"),  0,      20.0],
        [np.datetime64("2020-01-04", "ms"),  1,      30.0],
        [np.datetime64("2020-01-06", "ms"),  1,      40.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2

    isect_dates = provider.dates(Frequency.DAILY, DateSpan.INTERSECTION)
    assert len(isect_dates) == 2
    assert isinstance(isect_dates[0], datetime)
    assert isect_dates[0] == datetime(2020, 1, 4)
    assert isect_dates[1] == datetime(2020, 1, 5)

    r0_dates = provider.dates(Frequency.DAILY, DateSpan.INTERSECTION, realizations=[0])
    assert len(r0_dates) == 5

    r1_dates = provider.dates(Frequency.DAILY, DateSpan.INTERSECTION, realizations=[1])
    assert len(r1_dates) == 3


def test_get_vector_metadata(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",  "B_r",  "C_t",   "D_r_t"],
        [np.datetime64("2023-12-20", "ms"),  0,      1.0,  10.0,   21.0,    31.0 ],
        [np.datetime64("2023-12-20", "ms"),  1,      2.0,  12.0,   22.0,    32.0 ],
        [np.datetime64("2023-12-21", "ms"),  1,      3.0,  13.0,   23.0,    33.0 ],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    meta = provider.vector_metadata("A")
    assert meta is None

    meta = provider.vector_metadata("B_r")
    assert meta and meta.is_rate is True

    meta = provider.vector_metadata("C_t")
    assert meta and meta.is_total is True

    meta = provider.vector_metadata("D_r_t")
    assert meta and meta.is_rate is True
    assert meta and meta.is_total is True


def test_get_vectors_without_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",  "B"],
        [np.datetime64("2023-12-20", "ms"),  0,      10.0,  21.0],
        [np.datetime64("2023-12-20", "ms"),  1,      12.0,  22.0],
        [np.datetime64("2023-12-21", "ms"),  1,      13.0,  23.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_vecnames = provider.vector_names()
    assert len(all_vecnames) == 2

    vecdf = provider.get_vectors_df(["A"], resampling_options=None)
    assert vecdf.shape == (3, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime)

    vecdf = provider.get_vectors_df(["A"], resampling_options=None, realizations=[1])
    assert vecdf.shape == (2, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    vecdf = provider.get_vectors_df(
        ["B", "A"], resampling_options=None, realizations=[0]
    )
    assert vecdf.shape == (1, 4)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "B", "A"]


def test_get_vectors_with_daily_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-01", "ms"),  0,      10.0,     1.0],
        [np.datetime64("2020-01-04", "ms"),  0,      40.0,     4.0],
        [np.datetime64("2020-01-06", "ms"),  0,      60.0,     6.0],
        [np.datetime64("2020-01-05", "ms"),  1,      99.0,     9.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    vecdf = provider.get_vectors_df(
        ["TOT_t", "RATE_r"], ResamplingOptions(Frequency.DAILY, None)
    )

    r0_vecdf = vecdf[(vecdf["REAL"] == 0)]
    r1_vecdf = vecdf[(vecdf["REAL"] == 1)]

    r0_date_arr = r0_vecdf["DATE"].to_numpy()
    assert len(r0_date_arr) == 6
    assert r0_date_arr[0] == np.datetime64("2020-01-01", "ms")
    assert r0_date_arr[1] == np.datetime64("2020-01-02", "ms")
    assert r0_date_arr[2] == np.datetime64("2020-01-03", "ms")
    assert r0_date_arr[3] == np.datetime64("2020-01-04", "ms")
    assert r0_date_arr[4] == np.datetime64("2020-01-05", "ms")
    assert r0_date_arr[5] == np.datetime64("2020-01-06", "ms")

    r1_date_arr = r1_vecdf["DATE"].to_numpy()
    assert len(r1_date_arr) == 1
    assert r1_date_arr[0] == np.datetime64("2020-01-05", "ms")

    # Check interpolation for the total column
    r0_tot_arr = r0_vecdf["TOT_t"].to_numpy()
    assert r0_tot_arr[0] == 10
    assert r0_tot_arr[1] == 20
    assert r0_tot_arr[2] == 30
    assert r0_tot_arr[3] == 40
    assert r0_tot_arr[4] == 50
    assert r0_tot_arr[5] == 60

    r1_tot_arr = r1_vecdf["TOT_t"].to_numpy()
    assert r1_tot_arr[0] == 99

    # Check backfill for the rate column
    r0_rate_arr = r0_vecdf["RATE_r"].to_numpy()
    assert r0_rate_arr[0] == 1
    assert r0_rate_arr[1] == 4
    assert r0_rate_arr[2] == 4
    assert r0_rate_arr[3] == 4
    assert r0_rate_arr[4] == 6
    assert r0_rate_arr[5] == 6

    r1_rate_arr = r1_vecdf["RATE_r"].to_numpy()
    assert r1_rate_arr[0] == 9


def test_get_vectors_with_monthly_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-27", "ms"),  0,      10.0,     1.0],
        [np.datetime64("2020-02-06", "ms"),  0,      20.0,     2.0],
        [np.datetime64("2020-03-01", "ms"),  0,      30.0,     3.0],
        [np.datetime64("2020-03-15", "ms"),  0,      40.0,     4.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    vecdf = provider.get_vectors_df(
        ["TOT_t", "RATE_r"], ResamplingOptions(frequency=Frequency.MONTHLY)
    )

    date_arr = vecdf["DATE"].to_numpy()
    assert len(date_arr) == 4
    assert date_arr[0] == np.datetime64("2020-01-01", "ms")
    assert date_arr[1] == np.datetime64("2020-02-01", "ms")
    assert date_arr[2] == np.datetime64("2020-03-01", "ms")
    assert date_arr[3] == np.datetime64("2020-04-01", "ms")

    tot_arr = vecdf["TOT_t"].to_numpy()
    assert tot_arr[0] == 10
    assert tot_arr[1] == 15
    assert tot_arr[2] == 30
    assert tot_arr[3] == 40

    # Backfill for the rate column
    rate_arr = vecdf["RATE_r"].to_numpy()
    assert rate_arr[0] == 0
    assert rate_arr[1] == 2
    assert rate_arr[2] == 3
    assert rate_arr[3] == 0


def test_get_vectors_with_monthly_resampling_union(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-27", "ms"),  0,      10,       1],
        [np.datetime64("2020-02-06", "ms"),  0,      20,       2],
        [np.datetime64("2020-03-01", "ms"),  0,      30,       3],
        [np.datetime64("2020-03-15", "ms"),  0,      40,       4],
        [np.datetime64("2020-02-01", "ms"),  1,      992,      92],
        [np.datetime64("2020-03-01", "ms"),  1,      993,      93],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    vecdf = provider.get_vectors_df(
        ["TOT_t", "RATE_r"], ResamplingOptions(Frequency.MONTHLY, DateSpan.UNION)
    )
    assert vecdf.shape == (8, 4)

    r0_vecdf = vecdf[(vecdf["REAL"] == 0)]
    r1_vecdf = vecdf[(vecdf["REAL"] == 1)]
    assert r0_vecdf.shape == (4, 4)
    assert r1_vecdf.shape == (4, 4)

    r0_date_arr = r0_vecdf["DATE"].to_numpy()
    r1_date_arr = r1_vecdf["DATE"].to_numpy()
    assert r0_date_arr[0] == r1_date_arr[0] == np.datetime64("2020-01-01", "ms")
    assert r0_date_arr[1] == r1_date_arr[1] == np.datetime64("2020-02-01", "ms")
    assert r0_date_arr[2] == r1_date_arr[2] == np.datetime64("2020-03-01", "ms")
    assert r0_date_arr[3] == r1_date_arr[3] == np.datetime64("2020-04-01", "ms")

    r0_tot_arr = r0_vecdf["TOT_t"].to_numpy()
    assert r0_tot_arr[0] == 10
    assert r0_tot_arr[1] == 15
    assert r0_tot_arr[2] == 30
    assert r0_tot_arr[3] == 40

    r1_tot_arr = r1_vecdf["TOT_t"].to_numpy()
    assert r1_tot_arr[0] == 992
    assert r1_tot_arr[1] == 992
    assert r1_tot_arr[2] == 993
    assert r1_tot_arr[3] == 993

    r0_rate_arr = r0_vecdf["RATE_r"].to_numpy()
    assert r0_rate_arr[0] == 0
    assert r0_rate_arr[1] == 2
    assert r0_rate_arr[2] == 3
    assert r0_rate_arr[3] == 0

    r1_rate_arr = r1_vecdf["RATE_r"].to_numpy()
    assert r1_rate_arr[0] == 0
    assert r1_rate_arr[1] == 92
    assert r1_rate_arr[2] == 93
    assert r1_rate_arr[3] == 0


def test_get_vectors_with_monthly_resampling_intersection(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-27", "ms"),  0,      10,       1],
        [np.datetime64("2020-02-06", "ms"),  0,      20,       2],
        [np.datetime64("2020-03-01", "ms"),  0,      30,       3],
        [np.datetime64("2020-03-15", "ms"),  0,      40,       4],
        [np.datetime64("2020-02-01", "ms"),  1,      992,      92],
        [np.datetime64("2020-03-01", "ms"),  1,      993,      93],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    vecdf = provider.get_vectors_df(
        ["TOT_t", "RATE_r"], ResamplingOptions(Frequency.MONTHLY, DateSpan.INTERSECTION)
    )
    assert vecdf.shape == (4, 4)

    r0_vecdf = vecdf[(vecdf["REAL"] == 0)]
    r1_vecdf = vecdf[(vecdf["REAL"] == 1)]
    assert r0_vecdf.shape == (2, 4)
    assert r1_vecdf.shape == (2, 4)

    r0_date_arr = r0_vecdf["DATE"].to_numpy()
    r1_date_arr = r1_vecdf["DATE"].to_numpy()
    assert r0_date_arr[0] == r1_date_arr[0] == np.datetime64("2020-02-01", "ms")
    assert r0_date_arr[1] == r1_date_arr[1] == np.datetime64("2020-03-01", "ms")

    r0_tot_arr = r0_vecdf["TOT_t"].to_numpy()
    assert r0_tot_arr[0] == 15
    assert r0_tot_arr[1] == 30

    r1_tot_arr = r1_vecdf["TOT_t"].to_numpy()
    assert r1_tot_arr[0] == 992
    assert r1_tot_arr[1] == 993

    r0_rate_arr = r0_vecdf["RATE_r"].to_numpy()
    assert r0_rate_arr[0] == 2
    assert r0_rate_arr[1] == 3

    r1_rate_arr = r1_vecdf["RATE_r"].to_numpy()
    assert r1_rate_arr[0] == 92
    assert r1_rate_arr[1] == 93


def test_get_vectors_for_date_without_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A",   "B",   "C"],
        [np.datetime64("2023-12-20", "ms"),  0,      10.0,  21.0,  31.0 ],
        [np.datetime64("2023-12-20", "ms"),  1,      12.0,  22.0,  32.0 ],
        [np.datetime64("2023-12-21", "ms"),  1,      13.0,  23.0,  33.0 ],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    common_dates = provider.dates(
        resampling_frequency=None, date_span=DateSpan.INTERSECTION
    )
    assert len(common_dates) == 1

    date_to_get = common_dates[0]
    assert isinstance(date_to_get, datetime)

    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A"])
    assert vecdf.shape == (2, 2)
    assert vecdf.columns.tolist() == ["REAL", "A"]

    date_to_get = common_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "B"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "B"]

    date_to_get = common_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "C"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "C"]


def test_get_vectors_for_date_with_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-01", "ms"),  1,      10.0,     1.0],
        [np.datetime64("2020-01-04", "ms"),  1,      40.0,     4.0],
        [np.datetime64("2020-01-06", "ms"),  1,      60.0,     6.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    date_to_get = datetime(2020, 1, 3)

    df = provider.get_vectors_for_date_df(date_to_get, ["TOT_t", "RATE_r"])
    assert df.shape == (1, 3)

    assert df["REAL"][0] == 1
    assert df["TOT_t"][0] == 30.0
    assert df["RATE_r"][0] == 4.0
