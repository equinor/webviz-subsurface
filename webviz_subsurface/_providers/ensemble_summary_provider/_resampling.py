from dataclasses import dataclass
from typing import Dict

import numpy as np
import pyarrow as pa

from ._field_metadata import is_rate_from_field_meta
from .ensemble_summary_provider import Frequency


def _truncate_day_to_monday(datetime_day: np.datetime64) -> np.datetime64:
    # A bit hackish, utilizes the fact that datetime64 is relative to epoch
    # 1970-01-01 which is a Thursday
    return datetime_day.astype("datetime64[W]").astype("datetime64[D]") + 4


def _quarter_start_month(datetime_day: np.datetime64) -> np.datetime64:
    # A bit hackish, utilizes the fact that datetime64 is relative to epoch
    # 1970-01-01 which is the first day in Q1.
    datetime_month = np.datetime64(datetime_day, "M")
    return datetime_month - (datetime_month.astype(int) % 3)


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
    elif freq == Frequency.QUARTERLY:
        start = _quarter_start_month(min_date)
        stop = _quarter_start_month(max_date)
        if stop < max_date:
            stop += 3
        sampledates = np.arange(start, stop + 1, 3)
    elif freq == Frequency.YEARLY:
        start = np.datetime64(min_date, "Y")
        stop = np.datetime64(max_date, "Y")
        if stop < max_date:
            stop += 1
        sampledates = np.arange(start, stop + 1)
    else:
        raise NotImplementedError(
            f"Currently not supporting resampling to frequency {freq}."
        )

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

    padded_y = np.concatenate((yp, np.array([yright])))

    ret_arr = padded_y[indices]

    if x[0] < xp[0]:
        idx = np.searchsorted(x, xp[0])
        ret_arr[0:idx] = yleft

    return ret_arr


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
    # pylint: disable=too-many-locals

    real_arr_np = table.column("REAL").to_numpy()
    unique_reals, first_occurrence_idx, real_counts = np.unique(
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
            start_row_idx = first_occurrence_idx[i]
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


def _compute_interpolation_weight(
    d: np.datetime64, d0: np.datetime64, d1: np.datetime64
) -> float:
    # pylint: disable=invalid-name
    d_as_uint = d.astype(np.uint64)
    d0_as_uint = d0.astype(np.uint64)
    d1_as_uint = d1.astype(np.uint64)
    return float(d_as_uint - d0_as_uint) / float(d1_as_uint - d0_as_uint)


def sample_segmented_multi_real_table_at_date(
    table: pa.Table, np_datetime: np.datetime64
) -> pa.Table:
    """Sample table containing multiple realizations at the specified date.
    The table must contain both a REAL and a DATE column.
    The table must be segmented on REAL (so that all rows from a single
    realization are contiguous) and within each REAL segment, it must be
    sorted on DATE.
    """
    # pylint: disable=too-many-locals

    unique_reals_arr_np, first_occurrence_idx, real_counts = np.unique(
        table.column("REAL").to_numpy(), return_index=True, return_counts=True
    )

    all_dates_arr_np = table.column("DATE").to_numpy()

    # Will receive row indices into the full input table for the two values we should
    # interpolate/blend between.
    # To keep things simple we always add two indices for each realization even if
    # we know that no interpolation will be needed (e.g. exact matches)
    row_indices = []

    # Will receive the blending weights for doing interpolation
    interpolate_t_arr = np.zeros(len(unique_reals_arr_np))

    # Array with mask for selecting values when doing backfill. A value of 1 will select
    # v1, while a value of 0 will yield a 0 value
    backfill_mask_arr = np.ones(len(unique_reals_arr_np))

    for i, _real in enumerate(unique_reals_arr_np):
        # Starting row of this realization and number of rows belonging to realization
        start_row_idx = first_occurrence_idx[i]
        row_count = real_counts[i]

        # Get slice of the dates for just this realization
        dates_arr_np = all_dates_arr_np[start_row_idx : start_row_idx + row_count]
        assert len(dates_arr_np) > 0

        # OUTSIDE RANGE (query date is before our first date)
        if np_datetime < dates_arr_np[0]:
            row_indices.append(start_row_idx)
            row_indices.append(start_row_idx)
            # Extrapolate or just fill with 0 for rates
            # interpolate_t_arr[i] = 0
            backfill_mask_arr[i] = 0

        # OUTSIDE RANGE (query date is beyond our last date)
        elif np_datetime > dates_arr_np[-1]:
            row_indices.append(start_row_idx + row_count - 1)
            row_indices.append(start_row_idx + row_count - 1)
            # Extrapolate or just fill with 0 for rates. For interpolation, t should
            # really 1, but since the rows are duplicated it does not matter
            # interpolate_t_arr[i] = 0
            backfill_mask_arr[i] = 0

        # EXACT MATCH on the LAST DATE
        elif np_datetime == dates_arr_np[-1]:
            row_indices.append(start_row_idx + row_count - 1)
            row_indices.append(start_row_idx + row_count - 1)
            # interpolate_t_arr[i] = 0
            # backfill_mask_arr[i] = 1

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
                # Exact match
                row_indices.append(start_row_idx + last_insertion_index - 1)
                row_indices.append(start_row_idx + last_insertion_index - 1)
                # interpolate_t_arr[i] = 0
                # backfill_mask_arr[i] = 1
            else:
                row_indices.append(start_row_idx + last_insertion_index - 1)
                row_indices.append(start_row_idx + last_insertion_index)
                interpolate_t_arr[i] = _compute_interpolation_weight(
                    np_datetime,
                    dates_arr_np[last_insertion_index - 1],
                    dates_arr_np[last_insertion_index],
                )
                # backfill_mask_arr[i] = 1

    column_arrays = []

    for colname in table.schema.names:
        if colname == "REAL":
            column_arrays.append(unique_reals_arr_np)
        elif colname == "DATE":
            column_arrays.append(np.full(len(unique_reals_arr_np), np_datetime))
        else:
            records_np = table.column(colname).take(row_indices).to_numpy()
            if is_rate_from_field_meta(table.field(colname)):
                v1_arr = records_np[1::2]
                interpolated_vec_values = v1_arr * backfill_mask_arr
            else:
                v0_arr = records_np[0::2]
                v1_arr = records_np[1::2]
                delta_arr = v1_arr - v0_arr
                interpolated_vec_values = v0_arr + (delta_arr * interpolate_t_arr)

            column_arrays.append(pa.array(interpolated_vec_values))

    ret_table = pa.table(column_arrays, schema=table.schema)

    return ret_table
