import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ..._utils.perf_timer import PerfTimer
from ..ensemble_summary_provider._table_utils import (
    add_per_vector_min_max_to_table_schema_metadata,
    find_min_max_for_numeric_table_columns,
)
from ._field_metadata import create_column_metadata_from_field_meta
from .ensemble_table_provider import ColumnMetadata, EnsembleTableProvider

# Since PyArrow's actual compute functions are not seen by pylint
# pylint: disable=no-member


LOGGER = logging.getLogger(__name__)


def _sort_table_on_real(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(table, sort_keys=[("REAL", "ascending")])
    sorted_table = table.take(indices)
    return sorted_table


class EnsembleTableProviderImplArrow(EnsembleTableProvider):
    """This class implements a EnsembleTableProvider"""

    def __init__(self, arrow_file_name: Path) -> None:
        self._arrow_file_name = str(arrow_file_name)

        LOGGER.debug(f"init with arrow file: {self._arrow_file_name}")
        timer = PerfTimer()

        # We'll try and keep the file open for the life-span of the provider
        source = pa.memory_map(self._arrow_file_name, "r")
        et_open_ms = timer.lap_ms()

        self._cached_reader = pa.ipc.RecordBatchFileReader(source)
        et_create_reader_ms = timer.lap_ms()

        # Discover columns and realizations that are present in the arrow file
        column_names_on_file = self._cached_reader.schema.names
        self._column_names: List[str] = [
            colname
            for colname in column_names_on_file
            if colname not in ["REAL", "ENSEMBLE"]
        ]
        et_find_col_names_ms = timer.lap_ms()

        unique_realizations_on_file = (
            self._cached_reader.read_all().column("REAL").unique()
        )
        self._realizations: List[int] = unique_realizations_on_file.to_pylist()
        et_find_real_ms = timer.lap_ms()

        LOGGER.debug(
            f"init took: {timer.elapsed_s():.2f}s, "
            f"(open={et_open_ms}ms, create_reader={et_create_reader_ms}ms, "
            f"find_col_names={et_find_col_names_ms}ms, find_real={et_find_real_ms}ms), "
            f"#column_names={len(self._column_names)}, "
            f"#realization={len(self._realizations)}"
        )

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
        full_table = _sort_table_on_real(full_table)
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
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        table = pa.Table.from_pandas(ensemble_df, preserve_index=False)

        # The input DF may contain an ENSEMBLE column (which we'll drop before writing),
        # but it is probably an error if there is more than one unique value in it
        if "ENSEMBLE" in ensemble_df:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")
            table = table.drop(["ENSEMBLE"])

        # Write to arrow format
        arrow_file_name: Path = storage_dir / (storage_key + ".arrow")
        with pa.OSFile(str(arrow_file_name), "wb") as sink:
            with pa.RecordBatchFileWriter(sink, table.schema) as writer:
                writer.write_table(table)

    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleTableProviderImplArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleTableProviderImplArrow(arrow_file_name)

        return None

    def _get_or_read_schema(self) -> pa.Schema:
        if self._cached_reader:
            return self._cached_reader.schema

        source = pa.memory_map(self._arrow_file_name, "r")
        return pa.ipc.RecordBatchFileReader(source).schema

    def column_names(self) -> List[str]:
        return self._column_names

    def realizations(self) -> List[int]:
        return self._realizations

    def get_column_data(
        self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        timer = PerfTimer()

        # For now guard against requesting the same column multiple times since that
        # will cause the conversion to pandas below to throw
        # This should probably raise an exception instead?
        if len(set(column_names)) != len(column_names):
            LOGGER.warning("The column_names argument contains duplicate names")
            column_names = list(dict.fromkeys(column_names))

        # We always want to include the the REAL column but watch out in case it is
        # already included in the column_names list
        columns_to_get = (
            ["REAL", *column_names] if "REAL" not in column_names else column_names
        )

        table = self._cached_reader.read_all().select(columns_to_get)
        et_read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        et_filter_ms = timer.lap_ms()

        df = table.to_pandas(ignore_metadata=True)
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_column_data() took: {timer.elapsed_ms()}ms "
            f"(read={et_read_ms}ms, filter={et_filter_ms}ms, to_pandas={et_to_pandas_ms}ms), "
            f"#cols={len(column_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df

    def column_metadata(self, column_name: str) -> Optional[ColumnMetadata]:
        schema = self._get_or_read_schema()
        field = schema.field(column_name)
        return create_column_metadata_from_field_meta(field)
