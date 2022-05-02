import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._field_metadata import create_vector_metadata_from_field_meta
from ._resampling import (
    generate_normalized_sample_dates,
    resample_segmented_multi_real_table,
    sample_segmented_multi_real_table_at_date,
)
from ._table_utils import (
    add_per_vector_min_max_to_table_schema_metadata,
    find_intersected_dates_between_realizations,
    find_min_max_for_numeric_table_columns,
    get_per_vector_min_max_from_schema_metadata,
)
from .ensemble_summary_provider import (
    EnsembleSummaryProvider,
    Frequency,
    VectorMetadata,
)

# Since PyArrow's actual compute functions are not seen by pylint
# pylint: disable=no-member

LOGGER = logging.getLogger(__name__)


def _sort_table_on_real_then_date(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table, sort_keys=[("REAL", "ascending"), ("DATE", "ascending")]
    )
    sorted_table = table.take(indices)
    return sorted_table


def _is_date_column_monotonically_increasing(table: pa.Table) -> bool:
    dates_np = table.column("DATE").to_numpy()
    if not np.all(np.diff(dates_np) > np.timedelta64(0)):
        return False

    return True


def _find_first_non_increasing_date_pair(
    table: pa.Table,
) -> Tuple[Optional[np.datetime64], Optional[np.datetime64]]:
    dates_np = table.column("DATE").to_numpy()
    offending_indices = np.asarray(np.diff(dates_np) <= np.timedelta64(0)).nonzero()[0]
    if not offending_indices:
        return (None, None)

    return (dates_np[offending_indices[0]], dates_np[offending_indices[0] + 1])


class ProviderImplArrowLazy(EnsembleSummaryProvider):
    """This class implements an EnsembleSummaryProvider with lazy (on-demand)
    resampling/interpolation.
    """

    def __init__(self, arrow_file_name: Path) -> None:
        self._arrow_file_name = str(arrow_file_name)

        LOGGER.debug(f"init with arrow file: {self._arrow_file_name}")
        timer = PerfTimer()

        source = pa.memory_map(self._arrow_file_name, "r")
        et_open_ms = timer.lap_ms()

        reader = pa.ipc.RecordBatchFileReader(source)
        et_create_reader_ms = timer.lap_ms()

        # Discover columns and realizations that are present in the file
        column_names_on_file = reader.schema.names
        self._vector_names: List[str] = [
            colname
            for colname in column_names_on_file
            if colname not in ["DATE", "REAL", "ENSEMBLE"]
        ]
        et_find_vec_names_ms = timer.lap_ms()

        unique_realizations_on_file = reader.read_all().column("REAL").unique()
        self._realizations: List[int] = unique_realizations_on_file.to_pylist()
        et_find_real_ms = timer.lap_ms()

        # We'll try and keep the file open for the life-span of the provider.
        # Done to try and stop blobfuse from throwing the file out of its cache.
        self._cached_reader = reader

        # For testing, uncomment code below and we will be more aggressive
        # and keep the "raw" table in memory
        self._cached_full_table = None
        # self._cached_full_table = reader.read_all()

        LOGGER.debug(
            f"init took: {timer.elapsed_s():.2f}s, "
            f"(open={et_open_ms}ms, create_reader={et_create_reader_ms}ms, "
            f"find_vec_names={et_find_vec_names_ms}ms, find_real={et_find_real_ms}ms), "
            f"#vector_names={len(self._vector_names)}, "
            f"#realization={len(self._realizations)}"
        )

        if not self._realizations:
            raise ValueError("Init from backing store failed NO realizations")
        if not self._vector_names:
            raise ValueError("Init from backing store failed NO vector_names")

    @staticmethod
    def write_backing_store_from_per_realization_tables(
        storage_dir: Path, storage_key: str, per_real_tables: Dict[int, pa.Table]
    ) -> None:
        # pylint: disable=too-many-locals
        @dataclass
        class Elapsed:
            concat_tables_s: float = -1
            build_add_real_col_s: float = -1
            sorting_s: float = -1
            find_and_store_min_max_s: float = -1
            write_s: float = -1

        elapsed = Elapsed()

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        LOGGER.debug(f"Writing backing store to arrow file: {arrow_file_name}")
        timer = PerfTimer()

        unique_column_names = set()
        for real_num, table in per_real_tables.items():
            unique_column_names.update(table.schema.names)

            if "REAL" in table.schema.names:
                raise ValueError(
                    f"Input tables should not have REAL column (real={real_num})"
                )

            if table.schema.field("DATE").type != pa.timestamp("ms"):
                raise ValueError(
                    f"DATE column must have timestamp[ms] data type (real={real_num})"
                )

            if not _is_date_column_monotonically_increasing(table):
                offending_pair = _find_first_non_increasing_date_pair(table)
                raise ValueError(
                    f"DATE column must be monotonically increasing\n"
                    f"Error detected in realization: {real_num}\n"
                    f"First offending timestamps: {offending_pair}"
                )

        LOGGER.debug(
            f"Concatenating {len(per_real_tables)} tables with "
            f"{len(unique_column_names)} unique column names"
        )

        full_table = pa.concat_tables(per_real_tables.values(), promote=True)
        elapsed.concat_tables_s = timer.lap_s()

        real_arr = np.empty(full_table.num_rows, np.int32)
        table_start_idx = 0
        for real_num, real_table in per_real_tables.items():
            real_arr[table_start_idx : table_start_idx + real_table.num_rows] = real_num
            table_start_idx += real_table.num_rows

        full_table = full_table.add_column(0, "REAL", pa.array(real_arr))
        elapsed.build_add_real_col_s = timer.lap_s()

        # Must sort table on real since interpolations work per realization
        # and we utilize slicing for speed
        full_table = _sort_table_on_real_then_date(full_table)
        elapsed.sorting_s = timer.lap_s()

        # Find per column min/max values and store them as metadata on table's schema
        per_vector_min_max = find_min_max_for_numeric_table_columns(full_table)
        full_table = add_per_vector_min_max_to_table_schema_metadata(
            full_table, per_vector_min_max
        )
        elapsed.find_and_store_min_max_s = timer.lap_s()

        # feather.write_feather(full_table, dest=arrow_file_name)
        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, full_table.schema) as writer:
                writer.write_table(full_table)
        elapsed.write_s = timer.lap_s()

        LOGGER.debug(
            f"Wrote backing store to arrow file in: {timer.elapsed_s():.2f}s ("
            f"concat_tables={elapsed.concat_tables_s:.2f}s, "
            f"build_add_real_col={elapsed.build_add_real_col_s:.2f}s, "
            f"sorting={elapsed.sorting_s:.2f}s, "
            f"find_and_store_min_max={elapsed.find_and_store_min_max_s:.2f}s, "
            f"write={elapsed.write_s:.2f}s)"
        )

    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["ProviderImplArrowLazy"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return ProviderImplArrowLazy(arrow_file_name)

        return None

    def _get_or_read_schema(self) -> pa.Schema:
        if self._cached_full_table:
            return self._cached_full_table.schema
        if self._cached_reader:
            return self._cached_reader.schema

        source = pa.memory_map(self._arrow_file_name, "r")
        return pa.ipc.RecordBatchFileReader(source).schema

    def _get_or_read_table(self, columns: List[str]) -> pa.Table:
        if self._cached_full_table:
            return self._cached_full_table.select(columns)
        if self._cached_reader:
            return self._cached_reader.read_all().select(columns)

        source = pa.memory_map(self._arrow_file_name, "r")
        reader = pa.ipc.RecordBatchFileReader(source)
        return reader.read_all().select(columns)

    def vector_names(self) -> List[str]:
        return self._vector_names

    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:

        timer = PerfTimer()

        schema = self._get_or_read_schema()
        et_read_ms = timer.lap_ms()

        per_vector_min_max = get_per_vector_min_max_from_schema_metadata(schema)
        et_get_min_max_ms = timer.lap_ms()

        ret_vec_names: List[str] = []
        for vec_name in self._vector_names:
            minval = per_vector_min_max[vec_name]["min"]
            maxval = per_vector_min_max[vec_name]["max"]

            if minval == maxval:
                if exclude_constant_values:
                    continue

                if exclude_all_values_zero and minval == 0:
                    continue

            ret_vec_names.append(vec_name)
        et_filter_ms = timer.lap_ms()

        LOGGER.debug(
            f"vector_names_filtered_by_value() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"get_min_max={et_get_min_max_ms}ms, "
            f"filter={et_filter_ms}ms)"
        )

        return ret_vec_names

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        schema = self._get_or_read_schema()
        field = schema.field(vector_name)
        return create_vector_metadata_from_field_meta(field)

    def supports_resampling(self) -> bool:
        return True

    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:

        timer = PerfTimer()

        table = self._get_or_read_table(["DATE", "REAL"])
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        if resampling_frequency is not None:
            unique_dates_np = table.column("DATE").unique().to_numpy()
            min_raw_date = np.min(unique_dates_np)
            max_raw_date = np.max(unique_dates_np)
            intersected_dates = generate_normalized_sample_dates(
                min_raw_date, max_raw_date, resampling_frequency
            )
        else:
            intersected_dates = find_intersected_dates_between_realizations(table)

        et_find_unique_ms = timer.lap_ms()

        LOGGER.debug(
            f"dates({resampling_frequency}) took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"find_unique={et_find_unique_ms}ms)"
        )

        return intersected_dates.astype(datetime.datetime).tolist()

    def get_vectors_df(
        self,
        vector_names: Sequence[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        if not vector_names:
            raise ValueError("List of requested vector names is empty")

        timer = PerfTimer()

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table = self._get_or_read_table(columns_to_get)
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        if resampling_frequency is not None:
            table = resample_segmented_multi_real_table(table, resampling_frequency)
        et_resample_ms = timer.lap_ms()

        df = table.to_pandas(timestamp_as_object=True)
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_vectors_df({resampling_frequency}) took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"resample={et_resample_ms}ms, "
            f"to_pandas={et_to_pandas_ms}ms), "
            f"#vecs={len(vector_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df

    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        if not vector_names:
            raise ValueError("List of requested vector names is empty")

        timer = PerfTimer()

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table = self._get_or_read_table(columns_to_get)
        et_read_ms = timer.lap_ms()

        if realizations:
            real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(real_mask)
        et_filter_ms = timer.lap_ms()

        np_lookup_date = np.datetime64(date, "ms")
        table = sample_segmented_multi_real_table_at_date(table, np_lookup_date)

        et_resample_ms = timer.lap_ms()
        table = table.drop(["DATE"])

        df = table.to_pandas()
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_vectors_for_date_df() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"resample={et_resample_ms}ms, "
            f"to_pandas={et_to_pandas_ms}ms), "
            f"#vecs={len(vector_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df
