from typing import List, Optional, Sequence, Dict
import datetime
from pathlib import Path
import json
import logging

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather
import pandas as pd
import numpy as np

from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_dataframe_utils import (
    make_date_column_datetime_object,
)
from .ensemble_summary_provider_dataframe_utils import (
    find_min_max_for_numeric_columns,
)
from .._utils.perf_timer import PerfTimer


_MAIN_WEBVIZ_METADATA_KEY = b"webviz"
_PER_VECTOR_MIN_MAX_KEY = "per_vector_min_max"

LOGGER = logging.getLogger(__name__)

# Since PyArrow's actual compute functions are not seen by pylint
# pylint: disable=no-member


# -------------------------------------------------------------------------
def _create_float_downcasting_schema(schema: pa.Schema) -> pa.Schema:
    dt_float64 = pa.float64()
    dt_float32 = pa.float32()
    types = schema.types
    for idx, typ in enumerate(types):
        if typ == dt_float64:
            types[idx] = dt_float32

    field_list = zip(schema.names, types)
    return pa.schema(field_list)


# -------------------------------------------------------------------------
def _set_date_column_type_to_timestamp_us(schema: pa.Schema) -> pa.Schema:
    dt_timestamp_us = pa.timestamp("us")

    indexof_date_field = schema.get_field_index("DATE")

    types = schema.types
    types[indexof_date_field] = dt_timestamp_us

    field_list = zip(schema.names, types)
    return pa.schema(field_list)


# -------------------------------------------------------------------------
def _sort_table_on_date_and_real(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table, sort_keys=[("DATE", "ascending"), ("REAL", "ascending")]
    )
    sorted_table = table.take(indices)
    return sorted_table


# -------------------------------------------------------------------------
def _add_per_vector_min_max_to_table_schema_metadata(
    table: pa.Table, per_vector_min_max: Dict[str, dict]
) -> pa.Table:
    webviz_meta = {_PER_VECTOR_MIN_MAX_KEY: per_vector_min_max}
    new_combined_meta = {}
    new_combined_meta.update(table.schema.metadata)
    new_combined_meta.update({_MAIN_WEBVIZ_METADATA_KEY: json.dumps(webviz_meta)})
    table = table.replace_schema_metadata(new_combined_meta)
    return table


# -------------------------------------------------------------------------
def _get_per_vector_min_max_from_schema(schema: pa.Schema) -> Dict[str, dict]:
    webviz_meta = json.loads(schema.metadata[_MAIN_WEBVIZ_METADATA_KEY])
    return webviz_meta[_PER_VECTOR_MIN_MAX_KEY]


# -------------------------------------------------------------------------
def _dbg_sum_all_numeric_columns_in_table(table: pa.Table) -> None:
    timer = PerfTimer()

    num_cols = 0
    the_sum = 0
    for col in table.itercolumns():
        if col.type == pa.float64():
            col_sum = pc.sum(col).as_py()
            the_sum += col_sum
            num_cols += 1

    print(
        f"DBG DONE SUMMING  num_cols={num_cols}  the_sum={the_sum}  "
        f"time (ms): {timer.elapsed_ms()}"
    )


# =============================================================================
class EnsembleSummaryProviderImplArrow(EnsembleSummaryProvider):

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        LOGGER.debug(f"Writing backing store to arrow file: {arrow_file_name}")
        timer = PerfTimer()

        # Force data type in the incoming DataFrame's DATE column to datetime.datetime objects
        # This is the first step in coercing pyarrow to always store DATEs as timestamps
        ensemble_df = make_date_column_datetime_object(ensemble_df)
        et_convert_date_s = timer.lap_s()

        # Try and extract per column min/max values so we can store them in the arrow file
        # For now, we do this on the Pandas dataframe
        per_vector_min_max = find_min_max_for_numeric_columns(ensemble_df)
        et_find_min_max_s = timer.lap_s()

        # By default, we'll now end up with a schema that has timestamp[ns] for the DATE column
        # We therefore modify the retrieved schema and specify usage of timestamp[us] instead
        default_schema = pa.Schema.from_pandas(ensemble_df, preserve_index=False)
        schema_to_use = _set_date_column_type_to_timestamp_us(default_schema)

        # For experimenting with conversion to float
        do_convert_to_float32 = False
        if do_convert_to_float32:
            timer.lap_s()
            schema_to_use = _create_float_downcasting_schema(schema_to_use)
            LOGGER.info(
                f"Created schema for float downcasting in : {timer.lap_s():.2f}s"
            )

        timer.lap_s()
        table = pa.Table.from_pandas(
            ensemble_df, schema=schema_to_use, preserve_index=False
        )
        et_table_from_pandas_s = timer.lap_s()

        # We're done with the dataframe
        del ensemble_df

        # Attach our calculated min/max as metadata on table's schema
        table = _add_per_vector_min_max_to_table_schema_metadata(
            table, per_vector_min_max
        )

        timer.lap_ms()
        table = _sort_table_on_date_and_real(table)
        et_sorting_s = timer.lap_s()

        # with pa.OSFile(str(arrow_file_name), "wb") as sink:
        #     with pa.RecordBatchFileWriter(sink, table.schema) as writer:
        #         writer.write_table(table)

        # pa.feather.write_feather(
        #     table, dest=arrow_file_name, compression="uncompressed"
        # )

        pa.feather.write_feather(table, dest=arrow_file_name)

        et_write_s = timer.lap_s()

        LOGGER.debug(
            f"Wrote backing store to arrow file in: {timer.elapsed_s():.2f}s ("
            f"convert_date={et_convert_date_s:.2f}s, "
            f"find_min_max={et_find_min_max_s:.2f}s, "
            f"table_from_pandas={et_table_from_pandas_s:.2f}s, "
            f"sorting={et_sorting_s:.2f}s, "
            f"write={et_write_s:.2f}s)"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def write_backing_store_from_per_realization_dataframes_experimental(
        storage_dir: Path, storage_key: str, per_real_dfs: List[pd.DataFrame]
    ) -> None:

        """This implementation is a work in progress and is experimental.
        The idea is to let the caller avoid reading a large dataframe with all
        realizations and instead read separate dataframes for each realization.
        This should give a smaller memory footprint and should potentially be faster,
        but this has yet to be proven.
        NOTE! that currently this implementation is not complete as it does not extract
        and store per-column min/max values
        """

        LOGGER.debug("Writing backing store from PER REALIZATION DF to arrow file...")
        timer = PerfTimer()

        arrow_file_name = storage_dir / (storage_key + ".arrow")

        # For experimenting with conversion to float32
        do_convert_to_float32 = False

        table_list: List[pa.Table] = []
        for real_idx, real_df in enumerate(per_real_dfs):
            real_df = make_date_column_datetime_object(real_df)

            default_schema = pa.Schema.from_pandas(real_df, preserve_index=False)
            schema_to_use = _set_date_column_type_to_timestamp_us(default_schema)

            if do_convert_to_float32:
                schema_to_use = _create_float_downcasting_schema(schema_to_use)

            table = pa.Table.from_pandas(
                real_df, schema=schema_to_use, preserve_index=False
            )
            table_list.append(table)
        et_tables_from_pandas_s = timer.lap_s()

        table = pa.concat_tables(table_list, promote=True)
        et_concat_tables_s = timer.lap_s()

        real_arr = np.empty(table.num_rows, np.int64)
        table_start_idx = 0
        for real_idx, real_table in enumerate(table_list):
            real_arr[table_start_idx : table_start_idx + real_table.num_rows] = real_idx
            table_start_idx += real_table.num_rows

        table = table.add_column(0, "REAL", pa.array(real_arr))
        et_build_add_real_col_s = timer.lap_s()

        table = _sort_table_on_date_and_real(table)
        et_sorting_s = timer.lap_s()

        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, table.schema) as writer:
                writer.write_table(table)
        et_write_s = timer.lap_s()

        LOGGER.debug(
            f"Wrote backing store to arrow file in: {timer.elapsed_s():.2f}s ("
            f"tables_from_pandas={et_tables_from_pandas_s:.2f}s, "
            f"concat_tables={et_concat_tables_s:.2f}s, "
            f"build_add_real_col={et_build_add_real_col_s:.2f}s, "
            f"sorting={et_sorting_s:.2f}s, "
            f"write={et_write_s:.2f}s)"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleSummaryProviderImplArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleSummaryProviderImplArrow(arrow_file_name)

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

        per_vector_min_max = _get_per_vector_min_max_from_schema(schema)
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

        # table = self._get_or_read_table(self._vector_names)
        # ret_vec_names: List[str] = []
        # for vec_name in self._vector_names:
        #     minmax = pc.min_max(table[vec_name])
        #     if minmax.get("min") == minmax.get("max"):
        #         if exclude_constant_values:
        #             continue

        #         if exclude_all_values_zero and minmax.get("min") == pa.scalar(0.0):
        #             continue

        #     ret_vec_names.append(vec_name)

        # return ret_vec_names

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

        # _dbg_sum_all_numeric_columns_in_table(table)

        df = table.to_pandas(timestamp_as_object=True)
        # df = table.to_pandas(split_blocks=True, self_destruct=True)
        # del table  # not necessary, but a good practice
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_vectors_df() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
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

        # Note that we use us here to be aligned with storage type in arrow file
        lookup_date = pa.scalar(date, type=pa.timestamp("us"))
        mask = pc.equal(table["DATE"], lookup_date)

        if realizations:
            real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            mask = pc.and_(mask, real_mask)

        table = table.drop(["DATE"])

        # table = table.filter(mask).combine_chunks()
        table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        # _dbg_sum_all_numeric_columns_in_table(table)

        df = table.to_pandas()
        # df = table.to_pandas(split_blocks=True, zero_copy_only=True)
        # del table  # not necessary, but a good practice
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_vectors_for_date_df() took: {timer.elapsed_ms()}ms ("
            f"read={et_read_ms}ms, "
            f"filter={et_filter_ms}ms, "
            f"to_pandas={et_to_pandas_ms}ms), "
            f"#vecs={len(vector_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df
