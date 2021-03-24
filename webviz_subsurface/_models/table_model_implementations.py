from typing import List, Optional, Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pandas as pd

from .table_model import EnsembleTableModel

# =============================================================================
class EnsembleTableModelImplArrow(EnsembleTableModel):

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
    ) -> Optional["EnsembleTableModelImplArrow"]:

        arrow_file_name = storage_dir / (storage_key + ".arrow")
        if arrow_file_name.is_file():
            return EnsembleTableModelImplArrow(arrow_file_name)

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
        return df


# =============================================================================
class EnsembleTableModelImplInMemDataFrame(EnsembleTableModel):

    # -------------------------------------------------------------------------
    def __init__(self, ensemble_df: pd.DataFrame) -> None:
        # The input DF may contain an ENSEMBLE column, but it is probably an error if
        # There is more than one unique value in it
        if "ENSEMBLE" in ensemble_df:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")

        self._ensemble_df = ensemble_df
        self._realizations = list(self._ensemble_df["REAL"].unique())
        self._column_names: List[str] = [
            col
            for col in list(self._ensemble_df.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]

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

        if realizations:
            df = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations), ["REAL", *column_names]
            ]
        else:
            df = self._ensemble_df.loc[:, ["REAL", *column_names]]

        return df
