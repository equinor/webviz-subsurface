from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pyarrow as pa

from ._field_metadata import is_rate_from_field_meta
from ._table_utils import find_min_max_date_per_realization
from .ensemble_summary_provider import DateSpan, Frequency


def _truncate_day_to_monday(datetime_day: np.datetime64) -> np.datetime64:
    # A bit hackish, utilizes the fact that datetime64 is relative to epoch
    # 1970-01-01 which is a Thursday
    return datetime_day.astype("datetime64[W]").astype("datetime64[D]") + 4


def _quarter_start_month(datetime_day: np.datetime64) -> np.datetime64:
    # A bit hackish, utilizes the fact that datetime64 is relative to epoch
    # 1970-01-01 which is the first day in Q1.
    datetime_month = np.datetime64(datetime_day, "M")
    return datetime_month - (datetime_month.astype(int) % 3)


def _generate_normalized_sample_date_range_or_minmax(
    min_date: np.datetime64,
    max_date: np.datetime64,
    freq: Frequency,
    generate_full_range: bool,
) -> np.ndarray:
    """Worker function to determine the normalized sample dates that will cover the
    min_date to max_date interval with the specified frequency.
    If generate_full_range is True, an array containing the full range of sample dates
    will be returned. If False, only the min and max sample dates will be returned.
    The return numpy array will have sample dates with dtype datetime64[ms]
    """

    if freq == Frequency.DAILY:
        start = np.datetime64(min_date, "D")
        stop = np.datetime64(max_date, "D")
        step = 1
        if stop < max_date:
            stop += 1

    elif freq == Frequency.WEEKLY:
        start = _truncate_day_to_monday(np.datetime64(min_date, "D"))
        stop = _truncate_day_to_monday(np.datetime64(max_date, "D"))
        step = 7
        if start > min_date:
            start -= 7
        if stop < max_date:
            stop += 7

    elif freq == Frequency.MONTHLY:
        start = np.datetime64(min_date, "M")
        stop = np.datetime64(max_date, "M")
        step = 1
        if stop < max_date:
            stop += 1

    elif freq == Frequency.QUARTERLY:
        start = _quarter_start_month(min_date)
        stop = _quarter_start_month(max_date)
        step = 3
        if stop < max_date:
            stop += 3

    elif freq == Frequency.YEARLY:
        start = np.datetime64(min_date, "Y")
        stop = np.datetime64(max_date, "Y")
        step = 1
        if stop < max_date:
            stop += 1

    else:
        raise NotImplementedError(
            f"Currently not supporting resampling to frequency {freq}."
        )

    if generate_full_range:
        sampledates: np.ndarray = np.arange(start, stop + 1, step)
    else:
        sampledates = np.array([start, stop])

    return sampledates.astype("datetime64[ms]")


def generate_normalized_sample_dates(
    min_raw_date: np.datetime64, max_raw_date: np.datetime64, freq: Frequency
) -> np.ndarray:
    """Returns array of normalized sample dates to cover the min_raw_date to
    max_raw_date interval with the specified frequency.
    The return numpy array will have sample dates with dtype datetime64[ms]
    """
    return _generate_normalized_sample_date_range_or_minmax(
        min_date=min_raw_date,
        max_date=max_raw_date,
        freq=freq,
        generate_full_range=True,
    )


def get_normalized_min_max_sample_date(
    min_raw_date: np.datetime64, max_raw_date: np.datetime64, freq: Frequency
) -> Tuple[np.datetime64, np.datetime64]:
    """Returns min and max normalized sample dates to cover the min_raw_date to
    max_raw_date range with the specified frequency.
    The return tuple will have min and max dates with dtype datetime64[ms]
    """
    minmax_arr = _generate_normalized_sample_date_range_or_minmax(
        min_date=min_raw_date,
        max_date=max_raw_date,
        freq=freq,
        generate_full_range=False,
    )

    if len(minmax_arr) != 2:
        raise ValueError("Wrong number of array elements in minmax_arr")

    return (minmax_arr[0], minmax_arr[1])


def calc_intersection_of_normalized_date_intervals(
    raw_date_intervals: List[Tuple[np.datetime64, np.datetime64]], freq: Frequency
) -> Optional[Tuple[np.datetime64, np.datetime64]]:
    """Returns the intersection of the normalized version of all the intervals specified
    in raw_date_intervals.
    Note that each interval in raw_date_intervals will be normalized using the specified
    frequency before being used to calculate the intersection.
    """

    if not raw_date_intervals:
        return None

    first_raw_interval = raw_date_intervals[0]
    res_start, res_end = get_normalized_min_max_sample_date(
        first_raw_interval[0], first_raw_interval[1], freq
    )

    for raw_interval in raw_date_intervals[1:]:
        start, end = get_normalized_min_max_sample_date(
            raw_interval[0], raw_interval[1], freq
        )

        if start > res_end or end < res_start:
            return None

        res_start = max(res_start, start)
        res_end = min(res_end, end)

    return (res_start, res_end)


def find_union_of_normalized_dates(table: pa.Table, frequency: Frequency) -> np.ndarray:
    """Generates list of normalized sample dates, with the specified frequency, that
    covers the union of all dates in the table.
    """
    unique_dates_np = table.column("DATE").unique().to_numpy()
    if len(unique_dates_np) == 0:
        return np.empty(0, dtype=np.datetime64)

    min_raw_date = np.min(unique_dates_np)
    max_raw_date = np.max(unique_dates_np)
    return generate_normalized_sample_dates(min_raw_date, max_raw_date, frequency)


def find_intersection_of_normalized_dates(
    table: pa.Table, frequency: Frequency
) -> np.ndarray:
    """Generates list of normalized sample dates, with the specified frequency, that
    is the intersection of all the the normalized per-realization sample intervals.
    """
    # First find the raw date intervals for each realization.
    per_real_raw_intervals = find_min_max_date_per_realization(table)

    # Then calculate the intersection between the normalized versions of these intervals
    intersection_interval = calc_intersection_of_normalized_date_intervals(
        per_real_raw_intervals, frequency
    )
    if not intersection_interval:
        return np.empty(0, dtype=np.datetime64)

    return generate_normalized_sample_dates(
        intersection_interval[0],
        intersection_interval[1],
        frequency,
    )


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


class InterpolationHelper:
    """Helper class for tracking and caching of intermediate data needed when doing
    resampling of multi-realization table data.
    Assumes that table contains both a REAL and a DATE column.
    Also assumes that the table is segmented on REAL (so that all rows from a single
    realization are contiguous) and within each REAL segment, it must be sorted on DATE.
    """

    @dataclass(frozen=True)
    class RowSegment:
        start_row: int
        row_count: int

    @dataclass(frozen=True)
    class DateInfo:
        raw_dates_np_as_uint: np.ndarray
        sample_dates_np: np.ndarray
        sample_dates_np_as_uint: np.ndarray

    def __init__(
        self, table: pa.Table, freq: Frequency, common_date_span: Optional[DateSpan]
    ) -> None:
        real_arr_np = table.column("REAL").to_numpy()
        unique_reals, first_occurrence_idx, real_counts = np.unique(
            real_arr_np, return_index=True, return_counts=True
        )

        self._table = table
        self._frequency = freq

        self._real_row_segment_dict: Dict[int, InterpolationHelper.RowSegment] = {
            real: InterpolationHelper.RowSegment(
                start_row=first_occurrence_idx[idx], row_count=real_counts[idx]
            )
            for idx, real in enumerate(unique_reals)
        }

        self._real_date_info_dict: Dict[int, InterpolationHelper.DateInfo] = {}

        self.shared_sample_dates_np: Optional[np.ndarray] = None
        self.shared_sample_dates_np_as_uint: Optional[np.ndarray] = None
        if common_date_span is not None:
            if common_date_span == DateSpan.INTERSECTION:
                shared_dates = find_intersection_of_normalized_dates(table, freq)
            else:
                shared_dates = find_union_of_normalized_dates(table, freq)

            self.shared_sample_dates_np = shared_dates
            self.shared_sample_dates_np_as_uint = shared_dates.astype(np.uint64)

        # Try and prime the cache up front
        # for real in unique_reals:
        #     self.real_date_arrays(real)

    def unique_reals(self) -> List[int]:
        return list(self._real_row_segment_dict)

    def date_info(self, real: int) -> DateInfo:
        dateinfo = self._real_date_info_dict.get(real)
        if not dateinfo:
            seg = self._real_row_segment_dict[real]
            dates = self._table["DATE"].slice(seg.start_row, seg.row_count).to_numpy()

            if (
                self.shared_sample_dates_np is not None
                and self.shared_sample_dates_np_as_uint is not None
            ):
                dateinfo = InterpolationHelper.DateInfo(
                    raw_dates_np_as_uint=dates.astype(np.uint64),
                    sample_dates_np=self.shared_sample_dates_np,
                    sample_dates_np_as_uint=self.shared_sample_dates_np_as_uint,
                )
            else:
                min_raw_date = np.min(dates)
                max_raw_date = np.max(dates)
                sample_dates = generate_normalized_sample_dates(
                    min_raw_date, max_raw_date, self._frequency
                )

                dateinfo = InterpolationHelper.DateInfo(
                    raw_dates_np_as_uint=dates.astype(np.uint64),
                    sample_dates_np=sample_dates,
                    sample_dates_np_as_uint=sample_dates.astype(np.uint64),
                )

            self._real_date_info_dict[real] = dateinfo

        return dateinfo

    def row_segment(self, real: int) -> Tuple[int, int]:
        segment = self._real_row_segment_dict[real]
        return (segment.start_row, segment.row_count)


def resample_segmented_multi_real_table(
    table: pa.Table, freq: Frequency, common_date_span: Optional[DateSpan]
) -> pa.Table:
    """Resample table containing multiple realizations.
    The table must contain both a REAL and a DATE column.
    The table must be segmented on REAL (so that all rows from a single realization are
    contiguous) and within each REAL segment, it must be sorted on DATE.
    The segmentation is needed since interpolations must be done per realization
    and we utilize slicing on rows for speed.
    """

    # pylint: disable=too-many-locals

    helper = InterpolationHelper(table, freq, common_date_span)
    unique_reals = helper.unique_reals()

    output_columns_dict: Dict[str, pa.ChunkedArray] = {}

    for colname in table.schema.names:
        if colname in ["DATE", "REAL"]:
            continue

        is_rate = is_rate_from_field_meta(table.field(colname))
        raw_whole_numpy_arr = table.column(colname).to_numpy()

        vec_arr_list = []
        for real in unique_reals:
            start_row_idx, row_count = helper.row_segment(real)
            dateinfo = helper.date_info(real)

            raw_numpy_arr = raw_whole_numpy_arr[
                start_row_idx : start_row_idx + row_count
            ]

            if is_rate:
                inter = interpolate_backfill(
                    dateinfo.sample_dates_np_as_uint,
                    dateinfo.raw_dates_np_as_uint,
                    raw_numpy_arr,
                    0,
                    0,
                )
            else:
                inter = np.interp(
                    dateinfo.sample_dates_np_as_uint,
                    dateinfo.raw_dates_np_as_uint,
                    raw_numpy_arr,
                )

            arr_length = len(dateinfo.sample_dates_np_as_uint)
            assert arr_length == len(inter)

            vec_arr_list.append(inter)

        output_columns_dict[colname] = pa.chunked_array(vec_arr_list)

    date_arr_list = []
    real_arr_list = []
    for real in unique_reals:
        dateinfo = helper.date_info(real)
        arr_length = len(dateinfo.sample_dates_np)
        date_arr_list.append(dateinfo.sample_dates_np)
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
