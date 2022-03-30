import fnmatch
import re
from typing import List, Optional

import pandas as pd

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object
from webviz_subsurface._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
)
from webviz_subsurface._utils.vector_selector import add_vector_to_vector_selector_data


class SimulationTimeSeriesModel:
    """Class to process and and visualize ensemble timeseries"""

    REQUIRED_COLUMNS = ["ENSEMBLE", "REAL", "DATE"]

    def __init__(
        self,
        dataframe: pd.DataFrame,
        line_shape_fallback: str = "linear",
    ) -> None:

        for column in self.REQUIRED_COLUMNS:
            if column not in dataframe.columns:
                raise KeyError(f"{column} column is missing from UNSMRY data")

        dataframe = dataframe.copy()
        # ensure correct format of date
        dataframe["REAL"] = dataframe["REAL"].astype(int)
        dataframe["DATE"] = pd.to_datetime(dataframe["DATE"])
        make_date_column_datetime_object(dataframe)

        self._dataframe = self._remove_columns_with_only_0(dataframe)
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        self._dates = sorted(self._dataframe["DATE"].unique())
        self._vector_names = self._determine_vector_names()

        # add vectors to vector selector
        self.vector_selector_data: list = []
        for vector in self._vector_names:
            add_vector_to_vector_selector_data(self.vector_selector_data, vector)

    def _determine_vector_names(self) -> List[str]:
        """Determine which vectors we should make available"""
        return [c for c in self._dataframe if c not in self.REQUIRED_COLUMNS]

    @staticmethod
    def _remove_columns_with_only_0(dframe: pd.DataFrame) -> pd.DataFrame:
        """Filter list of vector names by removing vector names where the data is all zeros"""
        return dframe.loc[:, (dframe != 0).any(axis=0)]

    @property
    def dates(self) -> List[str]:
        return self._dates

    @property
    def dataframe(self) -> List[str]:
        return self._dataframe

    @property
    def vectors(self) -> List[str]:
        return self._vector_names

    @property
    def ensembles(self) -> List[str]:
        return list(self._dataframe["ENSEMBLE"].unique())

    def filter_vectors(self, column_keys: str):
        """Filter vector list used for correlation"""
        column_keys = "".join(column_keys.split()).split(",")
        try:
            regex = re.compile(
                "|".join([fnmatch.translate(col) for col in column_keys]),
                flags=re.IGNORECASE,
            )
            return [v for v in self.vectors if regex.fullmatch(v)]
        except re.error:
            return []

    def get_vector_df(
        self,
        ensemble: str,
        realizations: list,
        vectors: Optional[list] = None,
    ) -> pd.DataFrame:
        vectors = vectors if vectors is not None else self._vector_names
        df = self.dataframe[self.REQUIRED_COLUMNS + vectors].copy()
        return df.loc[
            (df["ENSEMBLE"] == ensemble) & (df["REAL"].isin(realizations)),
            ["DATE", "REAL"] + vectors,
        ]

    def get_historical_vector_df(
        self, vector: str, ensemble: str
    ) -> Optional[pd.DataFrame]:
        df = self._dataframe
        hist_vecname = historical_vector(vector, None)
        if hist_vecname and hist_vecname in df.columns:
            return (
                df[[hist_vecname, "DATE"]]
                .loc[
                    (df["REAL"] == df["REAL"].unique()[0])
                    & (df["ENSEMBLE"] == ensemble)
                ]
                .rename(columns={hist_vecname: vector})
            )
        return None
