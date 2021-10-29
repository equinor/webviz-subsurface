from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from ._field_metadata import is_rate_from_field_meta
from .ensemble_summary_provider import Frequency


def _truncate_day_to_monday(datetime_day: np.datetime64) -> np.datetime64:
    # A bit hackish, utilizes the fact that datetime64 is relative to epoch
    # 1970-01-01 which is a Thursday
    return datetime_day.astype("datetime64[W]").astype("datetime64[D]") + 4


def generate_normalized_sample_dates(
    min_date: np.datetime64, max_date: np.datetime64, freq: Frequency
) -> np.ndarray:
    """Returns array of normalized sample dates to cover the min_date to max_date
    range with the specified frequency.
    The return numpy array will have sample dates with dtype datetime64[ms]
    """

    if freq == Frequency.DAILY:
        start = np.datetime64(min_date, "D")
        stop = np.datetime64(max_date, "D")
        if stop < max_date:
            stop += 1
        sampledates = np.arange(start, stop + 1)
    elif freq == Frequency.WEEKLY:
        start = _truncate_day_to_monday(np.datetime64(min_date, "D"))
        stop = _truncate_day_to_monday(np.datetime64(max_date, "D"))
        if start > min_date:
            start -= 7
        if stop < max_date:
            stop += 7
        sampledates = np.arange(start, stop + 1, 7)
    elif freq == Frequency.MONTHLY:
        start = np.datetime64(min_date, "M")
        stop = np.datetime64(max_date, "M")
        if stop < max_date:
            stop += 1
        sampledates = np.arange(start, stop + 1)
    elif freq == Frequency.YEARLY:
        start = np.datetime64(min_date, "Y")
        stop = np.datetime64(max_date, "Y")
        if stop < max_date:
            stop += 1
        sampledates = np.arange(start, stop + 1)

    sampledates = sampledates.astype("datetime64[ms]")

    return sampledates


def interpolate_backfill(
    x: np.ndarray, xp: np.ndarray, yp: np.ndarray, yleft: float, yright: float
) -> np.ndarray:
    # pylint: disable=invalid-name
    """Do back-filling interpolation of the coordinates in xp and yp, evaluated at the
    x-coordinates specified in x.
    Note that xp and yp must be arrays of the same length.
    It is assumed that both the x and the xp array is sorted in increasing order.
    """

    # Finds the leftmost valid insertion indices for the values x in xp
    indices = np.searchsorted(xp, x, side="left")

    padded_y = np.concatenate((yp, [yright]))

    ret_arr = padded_y[indices]

    if x[0] < xp[0]:
        idx = np.searchsorted(x, xp[0])
        ret_arr[0:idx] = yleft

    return ret_arr

    # Naive approach that is way too slow
    # valcount = len(x)
    # y = np.zeros(valcount)
    # idx = 0
    # while idx < valcount:
    #     insidx = bisect.bisect_left(xp, x[idx])
    #     if insidx == 0 and x[idx] < xp[0]:
    #         yval = yleft
    #     elif insidx == len(xp):
    #         yval = yright
    #     else:
    #         yval = yp[insidx]

    #     y[idx] = yval

    #     idx += 1

    # return y


def resample_single_real_table(table: pa.Table, freq: Frequency) -> pa.Table:
    """Resample table that contains only a single realization.
    The table must contain a DATE column and it must be sorted on DATE
    """

    # Notes:
    # Getting meta data using json.loads() takes quite a bit of time!!
    # We should provide this info in another way.

    schema = table.schema

    raw_dates_np = table.column("DATE").to_numpy()
    raw_dates_np_as_uint = raw_dates_np.astype(np.uint64)

    min_raw_date = np.min(raw_dates_np)
    max_raw_date = np.max(raw_dates_np)

    sample_dates_np = generate_normalized_sample_dates(
        min_raw_date, max_raw_date, freq=freq
    )
    sample_dates_np_as_uint = sample_dates_np.astype(np.uint64)

    column_arrays = []

    for colname in schema.names:
        if colname == "DATE":
            column_arrays.append(sample_dates_np)
        elif colname == "REAL":
            column_arrays.append(
                np.full(len(sample_dates_np), table.column("REAL")[0].as_py())
            )
        else:
            raw_numpy_arr = table.column(colname).to_numpy()
            if is_rate_from_field_meta(table.field(colname)):
                i = interpolate_backfill(
                    sample_dates_np_as_uint, raw_dates_np_as_uint, raw_numpy_arr, 0, 0
                )
            else:
                i = np.interp(
                    sample_dates_np_as_uint, raw_dates_np_as_uint, raw_numpy_arr
                )

            column_arrays.append(i)

    ret_table = pa.table(column_arrays, schema=schema)

    return ret_table


def resample_multi_real_table_NAIVE(table: pa.Table, freq: Frequency) -> pa.Table:

    unique_reals = table.column("REAL").unique().to_pylist()
    # print("unique_reals:", unique_reals)

    resampled_tables_list = []

    for real in unique_reals:
        # pylint: disable=no-member
        mask = pc.is_in(table["REAL"], value_set=pa.array([real]))
        real_table = table.filter(mask)

        resampled_table = resample_single_real_table(real_table, freq)
        resampled_tables_list.append(resampled_table)

    full_resampled_table = pa.concat_tables(resampled_tables_list)
    return full_resampled_table


def resample_sorted_multi_real_table_NAIVE(
    table: pa.Table, freq: Frequency
) -> pa.Table:

    real_arr_np = table.column("REAL").to_numpy()
    unique_reals, first_occurence_idx, real_counts = np.unique(
        real_arr_np, return_index=True, return_counts=True
    )

    resampled_tables_list = []

    for i, _real in enumerate(unique_reals):
        start_row_idx = first_occurence_idx[i]
        row_count = real_counts[i]
        real_table = table.slice(start_row_idx, row_count)

        resampled_table = resample_single_real_table(real_table, freq)
        resampled_tables_list.append(resampled_table)

    full_resampled_table = pa.concat_tables(resampled_tables_list)
    return full_resampled_table


@dataclass
class RealInterpolationInfo:
    raw_dates_np: np.ndarray
    raw_dates_np_as_uint: np.ndarray
    sample_dates_np: np.ndarray
    sample_dates_np_as_uint: np.ndarray


def _extract_real_interpolation_info(
    table: pa.Table, start_row_idx: int, row_count: int, freq: Frequency
) -> RealInterpolationInfo:

    real_dates = table["DATE"].slice(start_row_idx, row_count).to_numpy()

    min_raw_date = np.min(real_dates)
    max_raw_date = np.max(real_dates)
    sample_dates = generate_normalized_sample_dates(min_raw_date, max_raw_date, freq)

    return RealInterpolationInfo(
        raw_dates_np=real_dates,
        raw_dates_np_as_uint=real_dates.astype(np.uint64),
        sample_dates_np=sample_dates,
        sample_dates_np_as_uint=sample_dates.astype(np.uint64),
    )


def resample_segmented_multi_real_table(table: pa.Table, freq: Frequency) -> pa.Table:
    """Resample table containing multiple realizations.
    The table must contain both a REAL and a DATE column.
    The table must be segmented on REAL (so that all rows from a single
    realization are contiguous) and within each REAL segment, it must be
    sorted on DATE.
    The segmentation is needed since interpolations must be done per realization
    and we utilize slicing on rows for speed.
    """

    real_arr_np = table.column("REAL").to_numpy()
    unique_reals, first_occurence_idx, real_counts = np.unique(
        real_arr_np, return_index=True, return_counts=True
    )

    output_columns_dict: Dict[str, pa.ChunkedArray] = {}

    real_interpolation_info_dict: Dict[int, RealInterpolationInfo] = {}

    for colname in table.schema.names:
        if colname in ["DATE", "REAL"]:
            continue

        is_rate = is_rate_from_field_meta(table.field(colname))
        raw_whole_numpy_arr = table.column(colname).to_numpy()

        vec_arr_list = []
        for i, real in enumerate(unique_reals):
            start_row_idx = first_occurence_idx[i]
            row_count = real_counts[i]

            rii = real_interpolation_info_dict.get(real)
            if not rii:
                rii = _extract_real_interpolation_info(
                    table, start_row_idx, row_count, freq
                )
                real_interpolation_info_dict[real] = rii

            raw_numpy_arr = raw_whole_numpy_arr[
                start_row_idx : start_row_idx + row_count
            ]

            if is_rate:
                inter = interpolate_backfill(
                    rii.sample_dates_np_as_uint,
                    rii.raw_dates_np_as_uint,
                    raw_numpy_arr,
                    0,
                    0,
                )
            else:
                inter = np.interp(
                    rii.sample_dates_np_as_uint,
                    rii.raw_dates_np_as_uint,
                    raw_numpy_arr,
                )

            arr_length = len(rii.sample_dates_np_as_uint)
            assert arr_length == len(inter)

            vec_arr_list.append(inter)

        output_columns_dict[colname] = pa.chunked_array(vec_arr_list)

    date_arr_list = []
    real_arr_list = []
    for real in unique_reals:
        rii = real_interpolation_info_dict[real]
        arr_length = len(rii.sample_dates_np)
        date_arr_list.append(rii.sample_dates_np)
        real_arr_list.append(np.full(arr_length, real))

    output_columns_dict["DATE"] = pa.chunked_array(date_arr_list)
    output_columns_dict["REAL"] = pa.chunked_array(real_arr_list)

    ret_table = pa.table(output_columns_dict, schema=table.schema)

    return ret_table


# Input table is expected to contain data for only a single
# realization and MUST be sorted on date
def sample_single_real_table_at_date_NAIVE_SLOW(
    table: pa.Table, np_datetime: np.datetime64
) -> pa.Table:

    # pylint: disable=invalid-name

    raw_dates_np = table.column("DATE").to_numpy()

    # last_insertion_index is the last legal insertion index of the queried value
    last_insertion_index: int = np.searchsorted(
        raw_dates_np, np_datetime, side="right"
    ).item()

    idx0 = -1
    idx1 = -1
    if last_insertion_index == len(raw_dates_np):
        # Either an exact match or outside the range (query date is beyond our last date)
        if raw_dates_np[last_insertion_index - 1] == np_datetime:
            idx0 = idx1 = last_insertion_index - 1
        else:
            idx0 = last_insertion_index - 1
            idx1 = -1
    elif last_insertion_index == 0:
        # Outside the range (query date is before our first date)
        idx0 = -1
        idx1 = 0
    else:
        assert raw_dates_np[last_insertion_index] > np_datetime
        if raw_dates_np[last_insertion_index - 1] == np_datetime:
            idx0 = idx1 = last_insertion_index - 1
        else:
            idx0 = last_insertion_index - 1
            idx1 = last_insertion_index

    # descr = "N/A"
    # if idx0 == idx1:
    #     assert idx0 >= 0
    #     descr = "exact"
    # elif idx0 == -1:
    #     assert idx1 == 0
    #     descr = "below"
    # elif idx1 == -1:
    #     assert idx0 == len(raw_dates_np) - 1
    #     descr = "above"
    # else:
    #     descr = "INTERPOLATE"

    # print(f"lookfor={np_datetime}   idx0={idx0}   idx1={idx1}   descr={descr}")

    row_indices = []
    if idx0 >= 0:
        row_indices.append(idx0)
    if idx1 >= 0 and idx1 != idx0:
        row_indices.append(idx1)

    records_table = table.take(row_indices)
    # print(records_table.shape)
    # print(type(records_table))

    t = 0
    if records_table.num_rows == 2:
        d_as_uint = np_datetime.astype(np.uint64)
        d0_as_uint = table.column("DATE").to_numpy()[0].astype(np.uint64)
        d1_as_uint = table.column("DATE").to_numpy()[1].astype(np.uint64)
        t = (d_as_uint - d0_as_uint) / (d1_as_uint - d0_as_uint)

    column_arrays = []
    for colname in table.schema.names:
        if colname == "REAL":
            column_arrays.append(np.array([table.column("REAL")[0].as_py()]))
        elif colname == "DATE":
            column_arrays.append(np.array([np_datetime]))
        else:
            # This is expensive wrt performance. Should optimize the function to avoid JSON parsing
            is_rate = is_rate_from_field_meta(table.field(colname))

            if idx0 == idx1:
                # Exact hit
                column_arrays.append(
                    pa.array([records_table.column(colname)[0].as_py()])
                )
            elif idx0 == -1 or idx1 == -1:
                # below or above (0 for rate, else extrapolate)
                assert records_table.num_rows == 1
                if is_rate:
                    column_arrays.append(pa.array([0.0]))
                else:
                    column_arrays.append(
                        pa.array([records_table.column(colname)[0].as_py()])
                    )
            else:
                # interpolate or backfill
                assert records_table.num_rows == 2
                if is_rate:
                    column_arrays.append(
                        pa.array([records_table.column(colname)[1].as_py()])
                    )
                else:
                    v0 = records_table.column(colname)[0].as_py()
                    v1 = records_table.column(colname)[1].as_py()
                    if v0 is not None and v1 is not None:
                        column_arrays.append(pa.array([v0 + t * (v1 - v0)]))
                    else:
                        column_arrays.append(pa.array([None], pa.float32()))

    ret_table = pa.table(column_arrays, schema=table.schema)

    return ret_table


# Table must be sorted on real, and then date!!!
def sample_sorted_multi_real_table_at_date_NAIVE_SLOW(
    table: pa.Table, np_datetime: np.datetime64
) -> pa.Table:

    real_arr_np = table.column("REAL").to_numpy()
    unique_reals, first_occurence_idx, real_counts = np.unique(
        real_arr_np, return_index=True, return_counts=True
    )

    tables_list = []

    for i, _real in enumerate(unique_reals):
        start_row_idx = first_occurence_idx[i]
        row_count = real_counts[i]
        real_table = table.slice(start_row_idx, row_count)

        single_row_table = sample_single_real_table_at_date_NAIVE_SLOW(
            real_table, np_datetime
        )
        tables_list.append(single_row_table)

    ret_table = pa.concat_tables(tables_list)
    return ret_table


class Classification(Enum):
    MUST_INTERPOLATE = 0
    EXACT_MATCH = 1
    OUTSIDE_RANGE = 2


@dataclass
class SamplingParams:
    classification: Classification
    t: float  # pylint: disable=invalid-name


def sample_segmented_multi_real_table_at_date(
    table: pa.Table, np_datetime: np.datetime64
) -> pa.Table:
    """Sample table containing multiple realizations at the specified date.
    The table must contain both a REAL and a DATE column.
    The table must be segmented on REAL (so that all rows from a single
    realization are contiguous) and within each REAL segment, it must be
    sorted on DATE.
    """
    # pylint: disable=invalid-name

    full_real_arr_np = table.column("REAL").to_numpy()
    unique_reals, first_occurence_idx, real_counts = np.unique(
        full_real_arr_np, return_index=True, return_counts=True
    )

    all_dates_arr_np = table.column("DATE").to_numpy()

    row_indices = []
    params_arr: List[SamplingParams] = []

    for i, _real in enumerate(unique_reals):
        start_row_idx = first_occurence_idx[i]
        row_count = real_counts[i]

        # Get slice of the dates for just this realization
        dates_arr_np = all_dates_arr_np[start_row_idx : start_row_idx + row_count]
        assert len(dates_arr_np) > 0

        if np_datetime < dates_arr_np[0]:
            # Outside the range (query date is before our first date)
            row_indices.append(start_row_idx)
            row_indices.append(start_row_idx)
            params_arr.append(SamplingParams(Classification.OUTSIDE_RANGE, 0))

        elif np_datetime >= dates_arr_np[-1]:
            # Either an exact match on the last date or outside the
            # range (query date is beyond our last date)
            row_indices.append(start_row_idx + row_count - 1)
            row_indices.append(start_row_idx + row_count - 1)
            if np_datetime == dates_arr_np[-1]:
                params_arr.append(SamplingParams(Classification.EXACT_MATCH, 0))
            else:
                params_arr.append(SamplingParams(Classification.OUTSIDE_RANGE, 0))

        else:
            # Search for query date amongst the realization's dates.
            # last_insertion_index is the last legal insertion index of the queried value
            last_insertion_index: int = np.searchsorted(
                dates_arr_np, np_datetime, side="right"
            ).item()

            assert 0 < last_insertion_index < len(dates_arr_np)
            assert dates_arr_np[last_insertion_index - 1] <= np_datetime
            assert dates_arr_np[last_insertion_index] > np_datetime

            if dates_arr_np[last_insertion_index - 1] == np_datetime:
                row_indices.append(start_row_idx + last_insertion_index - 1)
                row_indices.append(start_row_idx + last_insertion_index - 1)
                params_arr.append(SamplingParams(Classification.EXACT_MATCH, 0))
            else:
                row_indices.append(start_row_idx + last_insertion_index - 1)
                row_indices.append(start_row_idx + last_insertion_index)
                d_as_uint = np_datetime.astype(np.uint64)
                d0_as_uint = dates_arr_np[last_insertion_index - 1].astype(np.uint64)
                d1_as_uint = dates_arr_np[last_insertion_index].astype(np.uint64)
                t = (d_as_uint - d0_as_uint) / (d1_as_uint - d0_as_uint)
                params_arr.append(SamplingParams(Classification.MUST_INTERPOLATE, t))

    column_arrays = []
    for colname in table.schema.names:
        if colname == "REAL":
            column_arrays.append(unique_reals)
        elif colname == "DATE":
            column_arrays.append(np.full(len(unique_reals), np_datetime))
        else:
            is_rate = is_rate_from_field_meta(table.field(colname))

            records = table.column(colname).take(row_indices)
            records_np = records.to_numpy()

            interp_vec_values = []

            record_idx = 0
            for iparams in params_arr:
                v0 = records_np[record_idx]
                v1 = records_np[record_idx + 1]
                interp_val = None

                if iparams.classification == Classification.MUST_INTERPOLATE:
                    # Interpolate or backfill
                    if is_rate:
                        interp_val = v1
                    else:
                        if v0 is not None and v1 is not None:
                            interp_val = v0 + iparams.t * (v1 - v0)
                elif iparams.classification == Classification.EXACT_MATCH:
                    interp_val = v0
                elif iparams.classification == Classification.OUTSIDE_RANGE:
                    # Extrapolate or just fill with 0 for rates
                    if is_rate:
                        interp_val = 0
                    else:
                        interp_val = v0

                interp_vec_values.append(interp_val)
                record_idx += 2

            column_arrays.append(pa.array(interp_vec_values))

    ret_table = pa.table(column_arrays, schema=table.schema)
    return ret_table
