from typing import List, Optional, Sequence
import datetime

import pandas as pd

from .ensemble_time_series import EnsembleTimeSeries


# =============================================================================
class EnsembleTimeSeriesImplInMemDataFrame(EnsembleTimeSeries):

    # -------------------------------------------------------------------------
    def __init__(self, ensemble_df: pd.DataFrame) -> None:
        # The input DF may contain an ENSEMBLE column, but it is probably an error if
        # There is more than one unique value in it
        if "ENSEMBLE" in ensemble_df:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")

        self._ensemble_df = ensemble_df
        self._realizations = list(self._ensemble_df["REAL"].unique())
        self._vector_names: List[str] = [
            vecname
            for vecname in list(self._ensemble_df.columns)
            if vecname not in ["DATE", "REAL", "ENSEMBLE"]
        ]

    # -------------------------------------------------------------------------
    def vector_names(self) -> List[str]:
        return self._vector_names

    # -------------------------------------------------------------------------
    def vector_names_filtered_by_value(
        self,
        exclude_all_values_zero: bool = False,
        exclude_constant_values: bool = False,
    ) -> List[str]:

        df = self._ensemble_df[self._vector_names]
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
