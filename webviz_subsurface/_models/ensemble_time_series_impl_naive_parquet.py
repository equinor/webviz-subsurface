from typing import List, Optional, Sequence
import datetime
from pathlib import Path
import time

import pandas as pd

from .ensemble_time_series import EnsembleTimeSeries


# =============================================================================
class EnsembleTimeSeriesImplNaiveParquet(EnsembleTimeSeries):

    # -------------------------------------------------------------------------
    def __init__(self, parquet_file_name: Path) -> None:
        self._parquet_file_name = str(parquet_file_name)

        print(f"init with parquet file: {self._parquet_file_name}")
        lap_tim = time.perf_counter()

        df = pd.read_parquet(path=self._parquet_file_name)
        self._realizations = list(df["REAL"].unique())
        self._vector_names: List[str] = [
            col for col in list(df.columns) if col not in ["DATE", "REAL", "ENSEMBLE"]
        ]

        print(f"time to init from parquet (s): {(time.perf_counter() - lap_tim)}")

        if not self._realizations:
            raise ValueError("Init from backing store failed NO realizations")
        if not self._vector_names:
            raise ValueError("Init from backing store failed NO vector_names")

    # -------------------------------------------------------------------------
    @staticmethod
    def write_backing_store_from_ensemble_dataframe(
        storage_dir: Path, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:

        print(
            "entering EnsembleTimeSeriesImplNaiveParquet.write_backing_store_from_ensemble_dataframe() ..."
        )
        start_tim = time.perf_counter()

        parquet_file_name = storage_dir / (storage_key + ".parquet")
        ensemble_df.to_parquet(path=parquet_file_name)

        print(
            f"Total time in EnsembleTimeSeriesImplNaiveParquet.write_backing_store_from_ensemble_dataframe() (s): {(time.perf_counter() - start_tim)}"
        )

    # -------------------------------------------------------------------------
    @staticmethod
    def from_backing_store(
        storage_dir: Path, storage_key: str
    ) -> Optional["EnsembleTimeSeriesImplNaiveParquet"]:

        parquet_file_name = storage_dir / (storage_key + ".parquet")
        if parquet_file_name.is_file():
            return EnsembleTimeSeriesImplNaiveParquet(parquet_file_name)

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
        df = pd.read_parquet(path=self._parquet_file_name, columns=self._vector_names)
        desc_df = df.describe(percentiles=[])

        ret_vec_names: List[str] = []

        for vec_name in desc_df.columns:
            minval = desc_df[vec_name]["min"]
            maxval = desc_df[vec_name]["max"]

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
            df = pd.read_parquet(path=self._parquet_file_name, columns=["DATE", "REAL"])
            date_series = df.loc[df["REAL"].isin(realizations), "DATE"]
        else:
            df = pd.read_parquet(path=self._parquet_file_name, columns=["DATE"])
            date_series = df["DATE"]

        unique_date_vals = date_series.unique()
        return unique_date_vals

    # -------------------------------------------------------------------------
    def get_vectors_df(
        self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        columns_to_get = ["DATE", "REAL"]
        columns_to_get.extend(vector_names)
        df = pd.read_parquet(path=self._parquet_file_name, columns=columns_to_get)

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
        tmp_df = pd.read_parquet(path=self._parquet_file_name, columns=columns_to_read)

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
