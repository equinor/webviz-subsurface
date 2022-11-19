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

    REQUIRED_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]

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

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def realizations(self) -> List[int]:
        return list(self._dataframe["REAL"].unique())

    @staticmethod
    def _remove_columns_with_only_0(dframe: pd.DataFrame) -> pd.DataFrame:
        """Filter list of vector names by removing vector names where the data is all zeros"""
        return dframe.loc[:, (dframe != 0).any(axis=0)]

    @property
    def vectors(self) -> list:
        return self._vector_names

    def _determine_vector_names(self) -> List[str]:
        """Determine which vectors we should make available"""
        return [c for c in self._dataframe if c not in self.REQUIRED_COLUMNS]

    def ensembles(self) -> list:
        return list(self.dataframe["ENSEMBLE"].unique())

    def get_vector_df(
        self,
        ensemble: str,
        realizations: list,
        vectors: Optional[list] = None,
    ) -> pd.DataFrame:
        vectors = vectors if vectors is not None else self._vector_names
        df = self.dataframe[self.REQUIRED_COLUMNS + vectors].copy()
        realizations = realizations if realizations is not None else self.realizations
        return df.loc[
            (df["ENSEMBLE"] == ensemble) & (df["REAL"].isin(realizations)),
            ["DATE", "REAL"] + vectors,
        ]

    def get_last_date(self, ensemble: str) -> str:
        return self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]["DATE"].max()

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
