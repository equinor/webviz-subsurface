from typing import Optional, Sequence

import numpy as np
import pandas as pd


class ParametersModel:
    """Class to process and visualize ensemble parameter data"""

    REQUIRED_COLUMNS = ["REAL"]

    def __init__(self, dataframe: pd.DataFrame, drop_constants: bool = True) -> None:
        self._dataframe = dataframe
        self._prepare_data(drop_constants)

    def get_column_values_df(
        self, column_name: str, realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:

        if realizations:
            df = self._dataframe.loc[
                self._dataframe["REAL"].isin(realizations), ["REAL", column_name]
            ]
        else:
            df = self._dataframe.loc[:, ["REAL", column_name]]

        return df

    def _prepare_data(self, drop_constants: bool = True) -> None:
        """
        Different data preparations on the parameters, before storing them as an attribute.
        Option to drop parameters with constant values. Prefixes on parameters from GEN_KW
        are removed, in addition parameters with LOG distribution will be kept while the
        other is dropped.
        """
        self._dataframe = self._dataframe.reset_index(drop=True)

        if drop_constants:
            constant_params = [
                param
                for param in [
                    x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
                ]
                if len(self._dataframe[param].unique()) == 1
            ]
            self._dataframe = self._dataframe.drop(columns=constant_params)

        # Keep only LOG parameters
        log_params = [
            param.replace("LOG10_", "")
            for param in [
                x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
            ]
            if param.startswith("LOG10_")
        ]
        self._dataframe = self._dataframe.drop(columns=log_params)
        self._dataframe = self._dataframe.rename(
            columns={
                col: f"{col} (log)"
                for col in self._dataframe.columns
                if col.startswith("LOG10_")
            }
        )
        # Remove prefix on parameter name added by GEN_KW
        self._dataframe = self._dataframe.rename(
            columns={
                col: (col.split(":", 1)[1])
                for col in self._dataframe.columns
                if (":" in col and col not in self.REQUIRED_COLUMNS)
            }
        )
        # Drop columns if duplicate names
        self._dataframe = self._dataframe.loc[:, ~self._dataframe.columns.duplicated()]

        # Only use numeric columns and filter away REQUIRED_COLUMNS
        self._parameters = [
            x
            for x in self._dataframe.columns[
                [np.issubdtype(dtype, np.number) for dtype in self._dataframe.dtypes]
            ]
            if x not in self.REQUIRED_COLUMNS
        ]
