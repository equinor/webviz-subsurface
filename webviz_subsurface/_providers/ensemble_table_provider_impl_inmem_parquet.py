import logging
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from .._utils.perf_timer import PerfTimer
from .ensemble_table_provider import EnsembleTableProvider

LOGGER = logging.getLogger(__name__)


class EnsembleTableProviderImplInMemParquet(EnsembleTableProvider):
    def __init__(self, parquet_file_name: Path) -> None:
        self._ensemble_df = pd.read_parquet(path=parquet_file_name)
        self._realizations = list(self._ensemble_df["REAL"].unique())
        self._column_names: List[str] = [
            col
            for col in list(self._ensemble_df.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]

    @staticmethod
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        # The input DF may contain an ENSEMBLE column (which we'll drop before writing),
        # but it is probably an error if there is more than one unique value in it
        if "ENSEMBLE" in ensemble_df:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")

            ensemble_df = ensemble_df.drop(columns="ENSEMBLE")

        file_name = storage_dir / f"{storage_key}.inmem.parquet"
        ensemble_df.to_parquet(path=file_name)

    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleTableProviderImplInMemParquet"]:

        file_name = storage_dir / f"{storage_key}.inmem.parquet"
        if file_name.is_file():
            return EnsembleTableProviderImplInMemParquet(file_name)

        return None

    def column_names(self) -> List[str]:
        return self._column_names

    def realizations(self) -> List[int]:
        return self._realizations

    def get_column_data(
        self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        timer = PerfTimer()

        if realizations:
            df = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations), ["REAL", *column_names]
            ]
        else:
            df = self._ensemble_df.loc[:, ["REAL", *column_names]]

        LOGGER.debug(f"get_column_data() took: {timer.elapsed_ms()}ms")

        return df
