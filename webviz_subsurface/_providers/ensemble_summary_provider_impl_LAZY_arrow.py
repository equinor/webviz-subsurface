from typing import List, Optional, Sequence, Dict
import datetime
from pathlib import Path
import logging

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather
import pandas as pd
import numpy as np

from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_table_utils import (
    find_min_max_for_numeric_table_columns,
    add_per_vector_min_max_to_table_schema_metadata,
    get_per_vector_min_max_from_schema_metadata,
)
from .ensemble_summary_provider_resampling import (
    Frequency,
    resample_single_real_table,
    generate_normalized_sample_dates,
    resample_multi_real_table_NAIVE,
    resample_sorted_multi_real_table_NAIVE,
    resample_sorted_multi_real_table,
    sample_sorted_multi_real_table_at_date_NAIVE_SLOW,
    sample_sorted_multi_real_table_at_date_OPTIMIZED,
)
from .._utils.perf_timer import PerfTimer

# !!!!
# !!!!
# !!!!
# Temp for comparing DFs
# import datacompy

LOGGER = logging.getLogger(__name__)

# Since PyArrow's actual compute functions are not seen by pylint
# pylint: disable=no-member


DO_LAZY_RESAMPLING = True

# -------------------------------------------------------------------------
def _sort_table_on_real_then_date(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table, sort_keys=[("REAL", "ascending"), ("DATE", "ascending")]
    )
    sorted_table = table.take(indices)
    return sorted_table


# =============================================================================
class EnsembleSummaryProviderImplLAZYArrow(EnsembleSummaryProvider):

    # -------------------------------------------------------------------------
    def __init__(self, arrow_file_name: Path, sample_freq: Optional[Frequency]) -> None:
        self._arrow_file_name = str(arrow_file_name)
        self._sample_freq = sample_freq

        LOGGER.debug(f"init with arrow file: {self._arrow_file_name}")
        LOGGER.debug(f"init sample_freq: {repr(self._sample_freq)}")
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

    # -------------------------------------------------------------------------
    @staticmethod
    def write_backing_store_from_per_realization_tables(
        storage_dir: Path, storage_key: str, per_real_tables: Dict[int, pa.Table]
    ) -> None:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        LOGGER.debug(f"Writing backing store to arrow file: {arrow_file_name}")
        timer = PerfTimer()

        unique_column_names = set()
        for table in per_real_tables.values():
            unique_column_names.update(table.schema.names)
            date_type = table.schema.field("DATE").type
            if date_type != pa.timestamp("ms"):
                raise ValueError("DATE column must have timestamp[ms] data type")

        LOGGER.info(f"number of unique column names: {len(unique_column_names)}")
        LOGGER.info(f"number of tables to concatenate: {len(per_real_tables)}")

        full_table = pa.concat_tables(per_real_tables.values(), promote=True)
        et_concat_tables_s = timer.lap_s()

        real_arr = np.empty(full_table.num_rows, np.int32)
        table_start_idx = 0
        for real_num, real_table in per_real_tables.items():
            real_arr[table_start_idx : table_start_idx + real_table.num_rows] = real_num
            table_start_idx += real_table.num_rows

        full_table = full_table.add_column(0, "REAL", pa.array(real_arr))
        et_build_add_real_col_s = timer.lap_s()

        # Must sort table on real since interpolations work per realization
        # and we utilize slicing for speed
        full_table = _sort_table_on_real_then_date(full_table)
        et_sorting_s = timer.lap_s()

        # Find per column min/max values and store them as metadata on table's schema
        per_vector_min_max = find_min_max_for_numeric_table_columns(full_table)
        full_table = add_per_vector_min_max_to_table_schema_metadata(
            full_table, per_vector_min_max
        )
        et_find_and_store_min_max_s = timer.lap_s()

        # pa.feather.write_feather(full_table, dest=arrow_file_name)
        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, full_table.schema) as writer:
                writer.write_table(full_table)
        et_write_s = timer.lap_s()

        LOGGER.debug(
            f"Wrote backing store to arrow file in: {timer.elapsed_s():.2f}s ("
            f"concat_tables={et_concat_tables_s:.2f}s, "
            f"build_add_real_col={et_build_add_real_col_s:.2f}s, "
            f"sorting={et_sorting_s:.2f}s, "
            f"find_and_store_min_max={et_find_and_store_min_max_s:.2f}s, "
            f"write={et_write_s:.2f}s)"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str, sample_freq: Optional[Frequency]
    ) -> Optional["EnsembleSummaryProviderImplLAZYArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleSummaryProviderImplLAZYArrow(arrow_file_name, sample_freq)

        return None

    # -------------------------------------------------------------------------
    def _get_or_read_schema(self) -> pa.Schema:
        if self._cached_full_table:
            return self._cached_full_table.schema
        if self._cached_reader:
            return self._cached_reader.schema

        source = pa.memory_map(self._arrow_file_name, "r")
        return pa.ipc.RecordBatchFileReader(source).schema

    # -------------------------------------------------------------------------
    def _get_or_read_table(self, columns: List[str]) -> pa.Table:
        if self._cached_full_table:
            return self._cached_full_table.select(columns)
        if self._cached_reader:
            return self._cached_reader.read_all().select(columns)

        source = pa.memory_map(self._arrow_file_name, "r")
        reader = pa.ipc.RecordBatchFileReader(source)
        return reader.read_all().select(columns)

    # -------------------------------------------------------------------------
    def vector_names(self) -> List[str]:
        return self._vector_names

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    def realizations(self) -> List[int]:
        return self._realizations

    # -------------------------------------------------------------------------
    def dates(
        self, realizations: Optional[Sequence[int]] = None
    ) -> List[datetime.datetime]:

        timer = PerfTimer()

        table = self._get_or_read_table(["DATE", "REAL"])
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        if self._sample_freq is not None:
            unique_dates_np = table.column("DATE").unique().to_numpy()
            min_raw_date = np.min(unique_dates_np)
            max_raw_date = np.max(unique_dates_np)
            sample_dates_np = generate_normalized_sample_dates(
                min_raw_date, max_raw_date, self._sample_freq
            )
            unique_date_vals = sample_dates_np.astype(datetime.datetime).tolist()
        else:
            unique_date_vals = table.column("DATE").unique().to_pylist()
        et_find_unique_ms = timer.lap_ms()

        LOGGER.debug(
            f"dates() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"find_unique={et_find_unique_ms}ms)"
        )

        return unique_date_vals

    # -------------------------------------------------------------------------
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        timer = PerfTimer()

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table = self._get_or_read_table(columns_to_get)
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        if self._sample_freq is not None:
            # table = resample_multi_real_table_NAIVE(table, self._sample_freq)
            # table = resample_sorted_multi_real_table_NAIVE(table, self._sample_freq)
            table = resample_sorted_multi_real_table(table, self._sample_freq)
        et_resample_ms = timer.lap_ms()

        df = table.to_pandas(timestamp_as_object=True)
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_vectors_df() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"resample={et_resample_ms}ms, "
            f"to_pandas={et_to_pandas_ms}ms), "
            f"#vecs={len(vector_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df

    # -------------------------------------------------------------------------
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        timer = PerfTimer()

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table = self._get_or_read_table(columns_to_get)
        et_read_ms = timer.lap_ms()

        if self._sample_freq is not None:
            if realizations:
                real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
                table = table.filter(real_mask)
            et_filter_ms = timer.lap_ms()

            np_lookup_date = np.datetime64(date, "ms")
            table = sample_sorted_multi_real_table_at_date_OPTIMIZED(
                table, np_lookup_date
            )

            # !!!!!!
            # !!!!!!
            # Test code for comparing the two implementations
            # table_slow = sample_sorted_multi_real_table_at_date_NAIVE_SLOW(
            #     table, np_lookup_date
            # )

            # df_opt = table.to_pandas()
            # df_slow = table_slow.to_pandas()
            # compare = datacompy.Compare(
            #     df_slow, df_opt, on_index=True, abs_tol=0.000001
            # )
            # print(compare.report())

            et_resample_ms = timer.lap_ms()
            table = table.drop(["DATE"])

        else:
            # This scenario, without resampling, might not work very well unless all
            # the dates in all the realizations are aligned. Does an exact matching
            # on date, so the returned table may be missing realizations
            pa_lookup_date = pa.scalar(date, type=pa.timestamp("ms"))
            mask = pc.equal(table["DATE"], pa_lookup_date)

            if realizations:
                real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
                mask = pc.and_(mask, real_mask)

            table = table.drop(["DATE"])
            table = table.filter(mask)

            et_filter_ms = timer.lap_ms()
            et_resample_ms = 0

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
