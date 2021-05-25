from typing import List, Optional, Sequence
import datetime
from pathlib import Path
import logging

import pandas as pd
import pyarrow.parquet as pq
import numpy as np

from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_dataframe_utils import (
    make_date_column_datetime_object,
)
from .._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


# -------------------------------------------------------------------------
def _read_parquet_df(
    parquet_file_name: str, columns: Optional[List[str]]
) -> pd.DataFrame:
    # Using pd.read_parquet() will fail if year is beyond 2262
    # To remedy this, go via pa.Table so we can force timestamps to datetime objects
    table = pq.read_table(parquet_file_name, columns=columns)
    df = table.to_pandas(timestamp_as_object=True)
    return df


# =============================================================================
class EnsembleSummaryProviderImplParquet(EnsembleSummaryProvider):

    # -------------------------------------------------------------------------
    def __init__(self, parquet_file_name: Path) -> None:
        self._parquet_file_name = str(parquet_file_name)

        LOGGER.debug(f"init with parquet file: {self._parquet_file_name}")
        timer = PerfTimer()

        # Need to do better than reading the entire table here
        # Both wrt direct performance hit, but also wrt blobfuse caching
        df = _read_parquet_df(self._parquet_file_name, None)
        et_read_ms = timer.lap_ms()

        self._vector_names: List[str] = [
            col for col in list(df.columns) if col not in ["DATE", "REAL", "ENSEMBLE"]
        ]
        et_find_vec_names_ms = timer.lap_ms()

        self._realizations = list(df["REAL"].unique())
        et_find_real_ms = timer.lap_ms()

        LOGGER.debug(
            f"init took: {timer.elapsed_s():.2f}s, ("
            f"read={et_read_ms}ms, "
            f"find_vec_names={et_find_vec_names_ms}ms, find_real={et_find_real_ms}ms)"
        )

        if not self._realizations:
            raise ValueError("Init from backing store failed NO realizations")
        if not self._vector_names:
            raise ValueError("Init from backing store failed NO vector_names")

    # -------------------------------------------------------------------------
    @staticmethod
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        parquet_file_name = storage_dir / (storage_key + ".parquet")
        LOGGER.debug(f"Writing backing store to parquet file: {parquet_file_name}")
        timer = PerfTimer()

        ensemble_df = make_date_column_datetime_object(ensemble_df)

        ensemble_df.to_parquet(path=parquet_file_name)

        LOGGER.debug(
            f"Wrote backing store to parquet file in: {timer.elapsed_s():.2f}s"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleSummaryProviderImplParquet"]:

        parquet_file_name = storage_dir / (storage_key + ".parquet")
        if parquet_file_name.is_file():
            return EnsembleSummaryProviderImplParquet(parquet_file_name)

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

        # This is a naive, brute force technique
        # Should instead be able to read out statistical meta data from the parquet file
        # See https://mungingdata.com/pyarrow/parquet-metadata-min-max-statistics/
        df = _read_parquet_df(self._parquet_file_name, self._vector_names)

        ret_vec_names: List[str] = []

        for vec_name in self._vector_names:
            nparr = df[vec_name].values
            minval = np.nanmin(nparr)
            maxval = np.nanmax(nparr)

            if minval == maxval:
                if exclude_constant_values:
                    continue

                if exclude_all_values_zero and minval == 0:
                    continue

            ret_vec_names.append(vec_name)

        return ret_vec_names

    # -------------------------------------------------------------------------
    def realizations(self) -> List[int]:
        return self._realizations

    # -------------------------------------------------------------------------
    def dates(
        self, realizations: Optional[Sequence[int]] = None
    ) -> List[datetime.datetime]:

        if realizations:
            df = _read_parquet_df(self._parquet_file_name, ["DATE", "REAL"])
            date_series = df.loc[df["REAL"].isin(realizations), "DATE"]
        else:
            df = _read_parquet_df(self._parquet_file_name, ["DATE"])
            date_series = df["DATE"]

        # unique_date_vals = pd.to_datetime(date_series.unique())
        unique_date_vals = date_series.unique()
        return unique_date_vals

    # -------------------------------------------------------------------------
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        df = _read_parquet_df(self._parquet_file_name, columns_to_get)

        if realizations:
            df = df.loc[df["REAL"].isin(realizations), columns_to_get]

        return df

    # -------------------------------------------------------------------------
    def get_vectors_for_date_df(
        self,
        date: datetime.datetime,
        vector_names: Sequence[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:

        query_date = date

        columns_to_read = ["DATE", "REAL"]
        columns_to_read.extend(vector_names)
        tmp_df = _read_parquet_df(self._parquet_file_name, columns_to_read)

        columns_to_return = ["REAL"]
        columns_to_return.extend(vector_names)
        if realizations:
            df = tmp_df.loc[
                (tmp_df["DATE"] == query_date) & (tmp_df["REAL"].isin(realizations)),
                columns_to_return,
            ]
        else:
            df = tmp_df.loc[(tmp_df["DATE"] == query_date), columns_to_return]

        return df
