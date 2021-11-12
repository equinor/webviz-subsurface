import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from pyarrow import feather

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._dataframe_utils import make_date_column_datetime_object
from ._field_metadata import create_vector_metadata_from_field_meta
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


def _create_float_downcasting_schema(schema: pa.Schema) -> pa.Schema:
    dt_float64 = pa.float64()
    dt_float32 = pa.float32()
    types = schema.types
    for idx, typ in enumerate(types):
        if typ == dt_float64:
            types[idx] = dt_float32

    field_list = zip(schema.names, types)
    return pa.schema(field_list)


def _set_date_column_type_to_timestamp_ms(schema: pa.Schema) -> pa.Schema:
    dt_timestamp_ms = pa.timestamp("ms")

    indexof_date_field = schema.get_field_index("DATE")

    types = schema.types
    types[indexof_date_field] = dt_timestamp_ms

    field_list = zip(schema.names, types)
    return pa.schema(field_list)


def _sort_table_on_date_then_real(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table, sort_keys=[("DATE", "ascending"), ("REAL", "ascending")]
    )
    sorted_table = table.take(indices)
    return sorted_table


class ProviderImplArrowPresampled(EnsembleSummaryProvider):
    """Implements an EnsembleSummaryProvider without any resampling or interpolation"""

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
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:
        @dataclass
        class Elapsed:
            convert_date_s: float = -1
            table_from_pandas_s: float = -1
            find_and_store_min_max_s: float = -1
            sorting_s: float = -1
            write_s: float = -1

        elapsed = Elapsed()

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        LOGGER.debug(
            f"Writing backing store from ensemble dataframe to arrow file: {arrow_file_name}"
        )
        timer = PerfTimer()

        # Force data type in the incoming DataFrame's DATE column to datetime.datetime objects
        # This is the first step in coercing pyarrow to always store DATEs as timestamps
        ensemble_df = make_date_column_datetime_object(ensemble_df)
        elapsed.convert_date_s = timer.lap_s()

        # By default, we'll now end up with a schema that has timestamp[ns] for the DATE column
        # We therefore modify the retrieved schema and specify usage of timestamp[ms] instead
        default_schema = pa.Schema.from_pandas(ensemble_df, preserve_index=False)
        schema_to_use = _set_date_column_type_to_timestamp_ms(default_schema)

        # For experimenting with conversion to float
        # timer.lap_s()
        # schema_to_use = _create_float_downcasting_schema(schema_to_use)
        # LOGGER.info(
        #     f"Created schema for float downcasting in : {timer.lap_s():.2f}s"
        # )

        timer.lap_s()
        table = pa.Table.from_pandas(
            ensemble_df, schema=schema_to_use, preserve_index=False
        )
        elapsed.table_from_pandas_s = timer.lap_s()

        # We're done with the dataframe
        del ensemble_df

        # Find per column min/max values and then store them as metadata on table's schema
        timer.lap_ms()
        per_vector_min_max = find_min_max_for_numeric_table_columns(table)
        table = add_per_vector_min_max_to_table_schema_metadata(
            table, per_vector_min_max
        )
        elapsed.find_and_store_min_max_s = timer.lap_s()

        table = _sort_table_on_date_then_real(table)
        elapsed.sorting_s = timer.lap_s()

        # feather.write_feather(table, dest=arrow_file_name)
        feather.write_feather(table, dest=arrow_file_name, compression="uncompressed")
        elapsed.write_s = timer.lap_s()

        LOGGER.debug(
            f"Wrote backing store to arrow file in: {timer.elapsed_s():.2f}s ("
            f"convert_date={elapsed.convert_date_s:.2f}s, "
            f"table_from_pandas={elapsed.table_from_pandas_s:.2f}s, "
            f"find_and_store_min_max={elapsed.find_and_store_min_max_s:.2f}s, "
            f"sorting={elapsed.sorting_s:.2f}s, "
            f"write={elapsed.write_s:.2f}s)"
        )

    @staticmethod
    def write_backing_store_from_per_realization_tables(
        storage_dir: Path, storage_key: str, per_real_tables: Dict[int, pa.Table]
    ) -> None:
        @dataclass
        class Elapsed:
            concat_tables_s: float = -1
            build_add_real_col_s: float = -1
            sorting_s: float = -1
            find_and_store_min_max_s: float = -1
            write_s: float = -1

        elapsed = Elapsed()

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        LOGGER.debug(
            f"Writing backing store from per real tables to arrow file: {arrow_file_name}"
        )
        timer = PerfTimer()

        unique_column_names = set()
        for table in per_real_tables.values():
            unique_column_names.update(table.schema.names)
        LOGGER.debug(
            f"Concatenating {len(per_real_tables)} tables with "
            f"{len(unique_column_names)} unique column names"
        )

        timer.lap_s()
        full_table = pa.concat_tables(per_real_tables.values(), promote=True)
        elapsed.concat_tables_s = timer.lap_s()

        real_arr = np.empty(full_table.num_rows, np.int32)
        table_start_idx = 0
        for real_num, real_table in per_real_tables.items():
            real_arr[table_start_idx : table_start_idx + real_table.num_rows] = real_num
            table_start_idx += real_table.num_rows

        full_table = full_table.add_column(0, "REAL", pa.array(real_arr))
        elapsed.build_add_real_col_s = timer.lap_s()

        # Find per column min/max values and then store them as metadata on table's schema
        per_vector_min_max = find_min_max_for_numeric_table_columns(full_table)
        full_table = add_per_vector_min_max_to_table_schema_metadata(
            full_table, per_vector_min_max
        )
        elapsed.find_and_store_min_max_s = timer.lap_s()

        full_table = _sort_table_on_date_then_real(full_table)
        elapsed.sorting_s = timer.lap_s()

        # feather.write_feather(full_table, dest=arrow_file_name)
        feather.write_feather(
            full_table, dest=arrow_file_name, compression="uncompressed"
        )
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
    ) -> Optional["ProviderImplArrowPresampled"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return ProviderImplArrowPresampled(arrow_file_name)

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

    def realizations(self) -> List[int]:
        return self._realizations

    def vector_metadata(self, vector_name: str) -> Optional[VectorMetadata]:
        schema = self._get_or_read_schema()
        field = schema.field(vector_name)
        return create_vector_metadata_from_field_meta(field)

    def supports_resampling(self) -> bool:
        return False

    def dates(
        self,
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> List[datetime.datetime]:

        if resampling_frequency is not None:
            raise ValueError("Resampling is not supported by this provider")

        timer = PerfTimer()

        table = self._get_or_read_table(["DATE", "REAL"])
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        intersected_dates = find_intersected_dates_between_realizations(table)
        et_find_unique_ms = timer.lap_ms()

        LOGGER.debug(
            f"dates() took: {timer.elapsed_ms()}ms ("
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

        if resampling_frequency is not None:
            raise ValueError("Resampling is not supported by this provider")

        timer = PerfTimer()

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table = self._get_or_read_table(columns_to_get)
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

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

        # Note that we use MS here to be aligned with storage type in arrow file
        lookup_date = pa.scalar(date, type=pa.timestamp("ms"))
        mask = pc.equal(table["DATE"], lookup_date)

        if realizations:
            real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            mask = pc.and_(mask, real_mask)

        table = table.drop(["DATE"])

        # table = table.filter(mask).combine_chunks()
        table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

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
