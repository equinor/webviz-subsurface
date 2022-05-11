from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pytest

from webviz_subsurface._providers.ensemble_summary_provider._provider_impl_arrow_lazy import (
    Frequency,
    ProviderImplArrowLazy,
    _find_first_non_increasing_date_pair,
    _is_date_column_monotonically_increasing,
)
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    EnsembleSummaryProvider,
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


def test_get_dates_without_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "A"],
        [np.datetime64("2023-12-20", "ms"),  0,      10.0],
        [np.datetime64("2023-12-20", "ms"),  1,      12.0],
        [np.datetime64("2023-12-21", "ms"),  1,      13.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    all_realizations = provider.realizations()
    assert len(all_realizations) == 2

    all_dates = provider.dates(resampling_frequency=None)
    assert len(all_dates) == 1
    assert isinstance(all_dates[0], datetime)

    r0_dates = provider.dates(resampling_frequency=None, realizations=[0])
    r1_dates = provider.dates(resampling_frequency=None, realizations=[1])
    assert len(r0_dates) == 1
    assert len(r1_dates) == 2


def test_get_dates_with_daily_resampling(tmp_path: Path) -> None:
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

    all_dates = provider.dates(resampling_frequency=Frequency.DAILY)
    assert len(all_dates) == 6
    assert isinstance(all_dates[0], datetime)
    assert all_dates[0] == datetime(2020, 1, 1)
    assert all_dates[1] == datetime(2020, 1, 2)
    assert all_dates[4] == datetime(2020, 1, 5)
    assert all_dates[5] == datetime(2020, 1, 6)

    r0_dates = provider.dates(resampling_frequency=Frequency.DAILY, realizations=[0])
    assert len(r0_dates) == 4

    r1_dates = provider.dates(resampling_frequency=Frequency.DAILY, realizations=[1])
    assert len(r1_dates) == 1


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

    vecdf = provider.get_vectors_df(["A"], resampling_frequency=None)
    assert vecdf.shape == (3, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    sampleddate = vecdf["DATE"][0]
    assert isinstance(sampleddate, datetime)

    vecdf = provider.get_vectors_df(["A"], resampling_frequency=None, realizations=[1])
    assert vecdf.shape == (2, 3)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "A"]

    vecdf = provider.get_vectors_df(
        ["B", "A"], resampling_frequency=None, realizations=[0]
    )
    assert vecdf.shape == (1, 4)
    assert vecdf.columns.tolist() == ["DATE", "REAL", "B", "A"]


def test_get_vectors_with_daily_resampling(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                            "REAL",  "TOT_t",  "RATE_r"],
        [np.datetime64("2020-01-01", "ms"),  1,      10.0,     1.0],
        [np.datetime64("2020-01-04", "ms"),  1,      40.0,     4.0],
        [np.datetime64("2020-01-06", "ms"),  1,      60.0,     6.0],
    ]
    # fmt:on
    provider = _create_provider_obj_with_data(input_data, tmp_path)

    vecdf = provider.get_vectors_df(
        ["TOT_t", "RATE_r"], resampling_frequency=Frequency.DAILY
    )

    date_arr = vecdf["DATE"].to_numpy()
    assert date_arr[0] == np.datetime64("2020-01-01", "ms")
    assert date_arr[1] == np.datetime64("2020-01-02", "ms")
    assert date_arr[2] == np.datetime64("2020-01-03", "ms")
    assert date_arr[3] == np.datetime64("2020-01-04", "ms")
    assert date_arr[4] == np.datetime64("2020-01-05", "ms")
    assert date_arr[5] == np.datetime64("2020-01-06", "ms")

    # Check interpolation for the total column
    tot_arr = vecdf["TOT_t"].to_numpy()
    assert tot_arr[0] == 10
    assert tot_arr[1] == 20
    assert tot_arr[2] == 30
    assert tot_arr[3] == 40
    assert tot_arr[4] == 50
    assert tot_arr[5] == 60

    # Check backfill for the rate column
    tot_arr = vecdf["RATE_r"].to_numpy()
    assert tot_arr[0] == 1
    assert tot_arr[1] == 4
    assert tot_arr[2] == 4
    assert tot_arr[3] == 4
    assert tot_arr[4] == 6
    assert tot_arr[5] == 6


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

    all_dates = provider.dates(resampling_frequency=None)
    assert len(all_dates) == 1

    date_to_get = all_dates[0]
    assert isinstance(date_to_get, datetime)

    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A"])
    assert vecdf.shape == (2, 2)
    assert vecdf.columns.tolist() == ["REAL", "A"]

    date_to_get = all_dates[0]
    vecdf = provider.get_vectors_for_date_df(date_to_get, ["A", "B"], [0])
    assert vecdf.shape == (1, 3)
    assert vecdf.columns.tolist() == ["REAL", "A", "B"]

    date_to_get = all_dates[0]
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


def test_monotonically_increasing_date_util_functions() -> None:
    table_with_duplicate = pa.Table.from_pydict(
        {
            "DATE": [
                np.datetime64("2020-01-01", "ms"),
                np.datetime64("2020-01-02", "ms"),
                np.datetime64("2020-01-02", "ms"),
                np.datetime64("2020-01-03", "ms"),
            ],
        },
    )

    table_with_decrease = pa.Table.from_pydict(
        {
            "DATE": [
                np.datetime64("2020-01-01", "ms"),
                np.datetime64("2020-01-05", "ms"),
                np.datetime64("2020-01-04", "ms"),
                np.datetime64("2020-01-10", "ms"),
            ],
        },
    )

    assert not _is_date_column_monotonically_increasing(table_with_duplicate)
    offending_pair = _find_first_non_increasing_date_pair(table_with_duplicate)
    assert offending_pair[0] == np.datetime64("2020-01-02", "ms")
    assert offending_pair[1] == np.datetime64("2020-01-02", "ms")

    assert not _is_date_column_monotonically_increasing(table_with_decrease)
    offending_pair = _find_first_non_increasing_date_pair(table_with_decrease)
    assert offending_pair[0] == np.datetime64("2020-01-05", "ms")
    assert offending_pair[1] == np.datetime64("2020-01-04", "ms")


def test_create_with_repeated_dates(tmp_path: Path) -> None:
    # fmt:off
    input_data = [
        ["DATE",                                 "REAL", "A"],
        [np.datetime64("2000-01-02T00:00", "ms"), 1,     10.0],
        [np.datetime64("2500-12-20T23:59", "ms"), 1,     11.0],
        [np.datetime64("2500-12-20T23:59", "ms"), 1,     12.0],
    ]
    # fmt:on

    with pytest.raises(ValueError):
        _create_provider_obj_with_data(input_data, tmp_path)
