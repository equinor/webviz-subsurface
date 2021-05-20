from typing import List, Optional, Sequence
from pathlib import Path
import logging

import pyarrow as pa
import pyarrow.compute as pc
import pandas as pd

from .ensemble_table_provider import EnsembleTableProvider
from .._utils.perf_timer import PerfTimer


LOGGER = logging.getLogger(__name__)


# =============================================================================
class EnsembleTableProviderImplArrow(EnsembleTableProvider):

    # -------------------------------------------------------------------------
    def __init__(self, arrow_file_name: Path) -> None:
        self._arrow_file_name = str(arrow_file_name)

        LOGGER.debug(f"init with arrow file: {self._arrow_file_name}")
        timer = PerfTimer()

        # Discover columns and realizations that are present in the arrow file
        with pa.memory_map(self._arrow_file_name, "r") as source:
            reader = pa.ipc.RecordBatchFileReader(source)
            column_names_on_file = reader.schema.names
            unique_realizations_on_file = reader.read_all().column("REAL").unique()

        self._column_names: List[str] = [
            colname
            for colname in column_names_on_file
            if colname not in ["REAL", "ENSEMBLE"]
        ]
        self._realizations: List[int] = unique_realizations_on_file.to_pylist()

        LOGGER.debug(
            f"init took: {timer.elapsed_s():.2f}s, "
            f"#column_names={len(self._column_names)}, "
            f"#realization={len(self._realizations)}"
        )

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleTableProviderImplArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleTableProviderImplArrow(arrow_file_name)

        return None

    # -------------------------------------------------------------------------
    def column_names(self) -> List[str]:
        return self._column_names

    # -------------------------------------------------------------------------
    def realizations(self) -> List[int]:
        return self._realizations

    # -------------------------------------------------------------------------
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

        source = pa.memory_map(self._arrow_file_name, "r")
        table = pa.ipc.RecordBatchFileReader(source).read_all().select(columns_to_get)
        read_ms = timer.lap_ms()

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)
        filter_ms = timer.lap_ms()

        df = table.to_pandas(ignore_metadata=True)
        to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"get_column_data() took: {timer.elapsed_ms()}ms "
            f"(read={read_ms}ms, filter={filter_ms}ms, to_pandas={to_pandas_ms}ms), "
            f"#cols={len(column_names)}, "
            f"#real={len(realizations) if realizations else 'all'}, "
            f"df.shape={df.shape}, file={Path(self._arrow_file_name).name}"
        )

        return df
