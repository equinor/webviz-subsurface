from typing import List, Optional, Sequence, Dict
import datetime
from pathlib import Path
import time
import json

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather
import pandas as pd
import numpy as np

from .ensemble_time_series import EnsembleTimeSeries

_MAIN_WEBVIZ_METADATA_KEY = b"webviz"
_PER_VECTOR_MIN_MAX_KEY = "per_vector_min_max"


# -------------------------------------------------------------------------
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
# @profile
def _sort_table_on_date_and_real(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table, sort_keys=[("DATE", "ascending"), ("REAL", "ascending")]
    )
    sorted_table = table.take(indices)
    return sorted_table


# -------------------------------------------------------------------------
def _find_min_max_for_numeric_columns_in_df(
    df: pd.DataFrame,
) -> Dict[str, dict]:
    desc_df = df.describe(percentiles=[])
    ret_dict = {}
    for vec_name in desc_df.columns:
        minval = desc_df[vec_name]["min"]
        maxval = desc_df[vec_name]["max"]

        ret_dict[vec_name] = {"min": minval, "max": maxval}

    return ret_dict


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
            schema_to_use = _create_downcasting_schema(
                pa.Schema.from_pandas(ensemble_df, preserve_index=None)
            )
            print(
                f"  time figuring out schema for casting (s): {(time.perf_counter() - lap_tim)}"
            )

        lap_tim = time.perf_counter()
        table = pa.Table.from_pandas(
            ensemble_df, schema=schema_to_use, preserve_index=False
        )
        print(f"  time to convert from pandas (s): {(time.perf_counter() - lap_tim)}")

        # Try and extract per column min/max values so we can store them in the arrow file
        # For now, we do this on the Pandas dataframe
        lap_tim = time.perf_counter()
        per_vector_min_max = _find_min_max_for_numeric_columns_in_df(ensemble_df)
        print(f"  time to find min/max values (s): {(time.perf_counter() - lap_tim)}")

        # We're done with the dataframe
        del ensemble_df

        # Attach our calculated min/max as metadata on table's schema
        lap_tim = time.perf_counter()
        table = _add_per_vector_min_max_to_table_schema_metadata(
            table, per_vector_min_max
        )
        print(f"  time add min/max to schema (s): {(time.perf_counter() - lap_tim)}")

        if do_sorting:
            lap_tim = time.perf_counter()
            table = _sort_table_on_date_and_real(table)
            print(f"  time spend sorting table (s): {(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()

        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, table.schema) as writer:
                writer.write_table(table)

        # pa.feather.write_feather(
        #    table, dest=arrow_file_name, compression="uncompressed"
        # )

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
                new_schema = _create_downcasting_schema(org_schema)
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
            table = _sort_table_on_date_and_real(table)
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
    def vector_names(self) -> List[str]:
        return self._vector_names

    # -------------------------------------------------------------------------
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:

        source = pa.memory_map(self._arrow_file_name, "r")
        schema = pa.ipc.RecordBatchFileReader(source).schema
        per_vector_min_max = _get_per_vector_min_max_from_schema(schema)

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

        return ret_vec_names

        """
        ret_vec_names: List[str] = []
        for vec_name in self._vector_names:
            minmax = pc.min_max(table[vec_name])
            if minmax.get("min") == minmax.get("max"):
                if exclude_constant_values:
                    continue

                if exclude_all_values_zero and minmax.get("min") == pa.scalar(0.0):
                    continue

            ret_vec_names.append(vec_name)

        return ret_vec_names
        """

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

        lap_tim = time.perf_counter()
        source = pa.memory_map(self._arrow_file_name, "r")
        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        table: pa.Table = (
            pa.ipc.RecordBatchFileReader(source).read_all().select(columns_to_get)
        )
        print(f"  open and read (ms): {1000*(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        mask = pc.equal(table["DATE"], date)
        print(f"  create mask (ms): {1000*(time.perf_counter() - lap_tim)}")

        if realizations:
            real_mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            mask = pc.and_(mask, real_mask)

        lap_tim = time.perf_counter()
        table = table.drop(["DATE"])
        print(f"  drop date (ms): {1000*(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        # table = table.filter(mask).combine_chunks()
        table = table.filter(mask)
        print(f"  filter (ms): {1000*(time.perf_counter() - lap_tim)}")

        lap_tim = time.perf_counter()
        # df = table.to_pandas(split_blocks=True, zero_copy_only=True)
        df = table.to_pandas()
        print(f"  to pandas df (ms): {1000*(time.perf_counter() - lap_tim)}")

        return df
