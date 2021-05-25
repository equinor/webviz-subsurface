from typing import List, Optional, Sequence
import datetime
from pathlib import Path
import logging

import pandas as pd
import pyarrow.parquet as pq
import numpy as np

from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_dataframe_utils import (
    ensure_date_column_is_datetime_object,
)
from .._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


# =============================================================================
class EnsembleSummaryProviderImplInMemParquet(EnsembleSummaryProvider):

    # -------------------------------------------------------------------------
    def __init__(self, parquet_file_name: Path) -> None:

        LOGGER.debug(f"init with (INMEM) parquet file: {parquet_file_name}")
        timer = PerfTimer()

        # Using pd.read_parquet() will fail if year is beyond 2262
        # To remedy this, go via pa.Table so we can force timestamps to datetime objects
        table = pq.read_table(str(parquet_file_name))
        et_read_ms = timer.lap_ms()

        self._ensemble_df = table.to_pandas(timestamp_as_object=True)
        # self._ensemble_df = pd.read_parquet(path=parquet_file_name)
        et_to_pandas_ms = timer.lap_ms()

        LOGGER.debug(
            f"init took: {timer.elapsed_s():.2f}s, "
            f"(read={et_read_ms}ms, to_pandas={et_to_pandas_ms}ms)"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        file_name = storage_dir / (storage_key + ".inmem.parquet")
        LOGGER.debug(f"Writing backing store to (INMEM) parquet file: {file_name}")
        timer = PerfTimer()

        ensure_date_column_is_datetime_object(ensemble_df)

        ensemble_df.to_parquet(path=file_name)
        # ensemble_df.to_parquet(path=file_name, version="2.0", coerce_timestamps="ms")

        LOGGER.debug(
            f"Wrote backing store to (INMEM) parquet file in: {timer.elapsed_s():.2f}s"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleSummaryProviderImplInMemParquet"]:

        file_name = storage_dir / (storage_key + ".inmem.parquet")
        if file_name.is_file():
            return EnsembleSummaryProviderImplInMemParquet(file_name)

        return None

    # -------------------------------------------------------------------------
    def vector_names(self) -> List[str]:
        vector_names: List[str] = [
            col
            for col in list(self._ensemble_df.columns)
            if col not in ["DATE", "REAL", "ENSEMBLE"]
        ]

        return vector_names

    # -------------------------------------------------------------------------
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:

        # This is a naive, brute force technique
        # Should instead be able to read out statistical meta data from the parquet file
        # See https://mungingdata.com/pyarrow/parquet-metadata-min-max-statistics/
        ret_vec_names: List[str] = []

        for col_name in self._ensemble_df.columns:
            if col_name in ["DATE", "REAL", "ENSEMBLE"]:
                continue

            nparr = self._ensemble_df[col_name].values
            minval = np.nanmin(nparr)
            maxval = np.nanmax(nparr)

            if minval == maxval:
                if exclude_constant_values:
                    continue

                if exclude_all_values_zero and minval == 0:
                    continue

            ret_vec_names.append(col_name)

        return ret_vec_names

    # -------------------------------------------------------------------------
    def realizations(self) -> List[int]:
        realizations = list(self._ensemble_df["REAL"].unique())
        return realizations

    # -------------------------------------------------------------------------
    def dates(
        self, realizations: Optional[Sequence[int]] = None
    ) -> List[datetime.datetime]:

        if realizations:
            date_series = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations),
                "DATE",
            ]
        else:
            date_series = self._ensemble_df["DATE"]

        unique_date_vals = date_series.unique()
        return unique_date_vals

    # -------------------------------------------------------------------------
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)

        if realizations:
            df = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations),
                columns_to_get,
            ]
        else:
            df = self._ensemble_df.loc[:, columns_to_get]

        return df

    # -------------------------------------------------------------------------
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        query_date = date

        columns_to_get = ["REAL"]
        columns_to_get.extend(vector_names)

        if realizations:
            df = self._ensemble_df.loc[
                (self._ensemble_df["DATE"] == query_date)
                & (self._ensemble_df["REAL"].isin(realizations)),
                columns_to_get,
            ]
        else:
            df = self._ensemble_df.loc[
                (self._ensemble_df["DATE"] == query_date), columns_to_get
            ]

        return df
