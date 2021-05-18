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

        source = pa.memory_map(self._arrow_file_name, "r")
        table = (
            pa.ipc.RecordBatchFileReader(source)
            .read_all()
            .select(["REAL", *column_names])
        )

        if realizations:
            mask = pc.is_in(table["REAL"], value_set=pa.array(realizations))
            table = table.filter(mask)

        df = table.to_pandas()

        LOGGER.debug(
            f"get_column_data() took: {timer.elapsed_ms()}ms "
            f"(#columns={len(column_names)}, "
            f"#realizations={len(realizations) if realizations else 'all'})"
        )

        return df
