from typing import List
import pandas as pd


class TableModel:
    def __init__(
        self,
        dataframe: pd.DataFrame,
        selector_columns: List = None,
        filter_columns: List = None,
    ) -> None:
        self._dataframe = dataframe
        self._selector_columns = selector_columns if selector_columns else []
        self._filter_columns = filter_columns if filter_columns else []
        self._validate_input()

    @property
    def selector_columns(self) -> List:
        return self._selector_columns

    @property
    def filter_columns(self) -> List:
        return self._filter_columns

    @property
    def ensembles(self) -> List:
        return list(self._dataframe["ENSEMBLE"].unique())

    def realizations_in_ensemble(self, ensemble: str) -> List:
        return list(
            self._dataframe[self._dataframe["ENSEMBLE"] == ensemble]["REAL"].unique()
        )

    def _validate_input(self):
        for column in ["ENSEMBLE", "REAL"]:
            if column not in self._dataframe.columns:
                raise KeyError(f"Required column {column} is missing from input data")
        for column in self.selector_columns:
            if column not in self._dataframe.columns:
                raise KeyError(
                    f"Specified selector {column} is missing from input data"
                )
        for column in self.filter_columns:
            if column not in self._dataframe.columns:
                raise KeyError(f"Specified filter {column} is missing from input data")

    def get_column_values_for_ensemble(
        self, ensemble: str, column: str, realizations: List = None
    ):
        if column not in self._dataframe.columns:
            raise KeyError(f"column {column} is missing from input data")
