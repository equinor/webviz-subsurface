from typing import List, Optional, Sequence
import datetime
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.compute as pc
import pandas as pd
import numpy as np

from .ensemble_time_series import EnsembleTimeSeries


# =============================================================================
class EnsembleTimeSeriesImplArrow(EnsembleTimeSeries):

    # -------------------------------------------------------------------------
    def __init__(self, arrow_file_name: Path) -> None:
        self._arrow_file_name = str(arrow_file_name)

        print(f"init with arrow file: {self._arrow_file_name}")
        lap_tim = time.perf_counter()

        # Discover columns and realizations that are present in the arrow file
        with pa.memory_map(self._arrow_file_name, "r") as source:
            reader = pa.ipc.RecordBatchFileReader(source)
            column_names_on_file = reader.schema.names
            unique_realizations_on_file = reader.read_all().column("REAL").unique()

        self._vector_names: List[str] = [
            colname
            for colname in column_names_on_file
            if colname not in ["DATE", "REAL", "ENSEMBLE"]
        ]
        self._realizations: List[int] = unique_realizations_on_file.to_pylist()

        print(f"time to init from arrow (s): {(time.perf_counter() - lap_tim)}")

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

        print("entering write_backing_store_from_ensemble_dataframe() ...")
        start_tim = time.perf_counter()

        arrow_file_name = storage_dir / (storage_key + ".arrow")

        # For experimenting with sorting and conversion to float
        do_convert_to_float32 = False
        do_sorting = True

        schema_to_use: pa.Schema = None
        if do_convert_to_float32:
            lap_tim = time.perf_counter()
            schema_to_use = EnsembleTimeSeriesImplArrow._create_downcasting_schema(
                pa.Schema.from_pandas(ensemble_df, preserve_index=None)
            )
            print(
                f"  time figuring out schema for casting (s): {(time.perf_counter() - lap_tim)}"
            )

        lap_tim = time.perf_counter()
        table = pa.Table.from_pandas(
            ensemble_df, schema=schema_to_use, preserve_index=False
        )
        del ensemble_df
        print(f"  time to convert from pandas (s): {(time.perf_counter() - lap_tim)}")

        if do_sorting:
            lap_tim = time.perf_counter()
            table = EnsembleTimeSeriesImplArrow._sort_table_on_date_and_real(table)
            print(f"  time spend sorting table (s): {(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, table.schema) as writer:
                writer.write_table(table)
        print(
            f"  time writing arrow (s): {(time.perf_counter() - lap_tim)}   fn: {arrow_file_name}"
        )

        print(
            f"Total time in write_backing_store_from_ensemble_dataframe (s): {(time.perf_counter() - start_tim)}"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def write_backing_store_from_per_realization_dataframes(
        storage_dir: Path, storage_key: str, per_real_dfs: List[pd.DataFrame]
    ) -> None:

        print("entering write_backing_store_from_per_realization_dataframes() ...")
        start_tim = time.perf_counter()

        arrow_file_name = storage_dir / (storage_key + ".arrow")

        # For experimenting with sorting and conversion to float
        do_convert_to_float32 = False
        do_sorting = True

        lap_tim = time.perf_counter()

        table_list: List[pa.Table] = []
        for real_idx, real_df in enumerate(per_real_dfs):
            if do_convert_to_float32:
                org_schema = pa.Schema.from_pandas(real_df, preserve_index=False)
                new_schema = EnsembleTimeSeriesImplArrow._create_downcasting_schema(
                    org_schema
                )
                table = pa.Table.from_pandas(
                    real_df, schema=new_schema, preserve_index=False
                )
            else:
                table = pa.Table.from_pandas(real_df, preserve_index=False)

            table_list.append(table)

        print(f"  time to convert from pandas (s): {(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        table = pa.concat_tables(table_list, promote=True)
        print(f"  time to build table (s): {(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        real_arr = np.empty(table.num_rows, np.int64)
        table_start_idx = 0
        for real_idx, real_table in enumerate(table_list):
            real_arr[table_start_idx : table_start_idx + real_table.num_rows] = real_idx
            table_start_idx += real_table.num_rows

        table = table.add_column(0, "REAL", pa.array(real_arr))
        print(
            f"  time to build and add real column (s): {(time.perf_counter() - lap_tim)}"
        )

        if do_sorting:
            lap_tim = time.perf_counter()
            table = EnsembleTimeSeriesImplArrow._sort_table_on_date_and_real(table)
            print(f"  time spend sorting table (s): {(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, table.schema) as writer:
                writer.write_table(table)
        print(
            f"  time to write to arrow (s): {(time.perf_counter() - lap_tim)}   fn: {arrow_file_name}"
        )

        print(
            f"Total time in write_backing_store_from_per_realization_dataframes (s): {(time.perf_counter() - start_tim)}"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleTimeSeriesImplArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleTimeSeriesImplArrow(arrow_file_name)

        return None

    # -------------------------------------------------------------------------
    @staticmethod
    def _create_downcasting_schema(schema: pa.Schema) -> pa.Schema:
        dt_float64 = pa.float64()
        dt_float32 = pa.float32()
        types = schema.types
        for i, t in enumerate(types):
            if t == dt_float64:
                types[i] = dt_float32

        field_list = zip(schema.names, types)
        return pa.schema(field_list)

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def _sort_table_on_date_and_real(table: pa.Table) -> pa.Table:
        indices = pc.sort_indices(
            table, sort_keys=[("DATE", "ascending"), ("REAL", "ascending")]
        )
        sorted_table = table.take(indices)
        return sorted_table

    # -------------------------------------------------------------------------
    def vector_names(self) -> List[str]:
        return self._vector_names

    # -------------------------------------------------------------------------
    def realizations(self) -> List[int]:
        return self._realizations

    # -------------------------------------------------------------------------
    def dates(
        self, realizations: Optional[Sequence[int]] = None
    ) -> List[datetime.datetime]:
        source = pa.memory_map(self._arrow_file_name, "r")
        table: pa.Table = (
            pa.ipc.RecordBatchFileReader(source).read_all().select(["DATE", "REAL"])
        )

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)

        unique_date_vals = table.column("DATE").unique()
        return unique_date_vals
        # return unique_date_vals.to_pylist()

    # -------------------------------------------------------------------------
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        # Here we open the file each time we want to read data
        # We can optimize this by keeping the file open, but should investigate andy downsides
        source = pa.memory_map(self._arrow_file_name, "r")

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table: pa.Table = (
            pa.ipc.RecordBatchFileReader(source).read_all().select(columns_to_get)
        )

        if realizations:
            # mask = pc.equal(table["REAL"], pa.scalar(3))
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            df = table.filter(mask).to_pandas()
        else:
            df = table.to_pandas()
            # df = table.to_pandas(split_blocks=True, self_destruct=True)

        # df = table.to_pandas(split_blocks=True, self_destruct=True)
        # del table  # not necessary, but a good practice

        return df

    # -------------------------------------------------------------------------
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        source = pa.memory_map(self._arrow_file_name, "r")

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table: pa.Table = (
            pa.ipc.RecordBatchFileReader(source).read_all().select(columns_to_get)
        )

        mask = pc.equal(table["DATE"], date)

        if realizations:
            real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            mask = pc.and_(mask, real_mask)

        table = table.drop(["DATE"])
        df = table.filter(mask).to_pandas()

        return df
