from typing import List, Dict, Optional, Sequence
from pathlib import Path

import pandas as pd
import numpy as np

from .table_model import EnsembleTableModel


class EnsembleTableModel_dataFrameBacked(EnsembleTableModel):
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

    def column_names(self) -> List[str]:
        return self._column_names

    def realizations(self) -> List[int]:
        return self._realizations

    def get_column_values_numpy(
        self, column_name: str, realizations: Optional[Sequence[int]] = None
    ) -> List[np.ndarray]:
        if realizations is None:
            realizations = self._realizations

        ret_list: List[np.ndarray] = []
        for real in realizations:
            series = self._ensemble_df.loc[
                self._ensemble_df["REAL"] == real, column_name
            ]
            arr = series.to_numpy()
            ret_list.append(arr)

        return ret_list

    def get_column_values_df(
        self, column_name: str, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        if realizations:
            df = self._ensemble_df.loc[
                self._ensemble_df["REAL"].isin(realizations), ["REAL", column_name]
            ]
        else:
            df = self._ensemble_df.loc[:, ["REAL", column_name]]

        return df
