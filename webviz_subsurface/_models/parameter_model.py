import numpy as np
import pandas as pd


class ParametersModel:
    """Class to process ensemble parameter data"""

    POSSIBLE_SELECTORS = [
        "ENSEMBLE",
        "REAL",
        "SENSNAME",
        "SENSCASE",
        "SENSTYPE",
    ]

    def __init__(
        self,
        dataframe: pd.DataFrame,
        drop_constants: bool = True,
        keep_numeric_only: bool = True,
    ) -> None:
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
        self._sensrun = self._check_if_sensitivity_run()
        self._prepare_data(drop_constants, keep_numeric_only)
        self._parameters = [
            x for x in self._dataframe if x not in self.POSSIBLE_SELECTORS
        ]

    @property
    def parameters(self) -> list:
        return self._parameters

    @property
    def selectors(self) -> list:
        return [col for col in self.POSSIBLE_SELECTORS if col in self.dataframe]

    @property
    def sensitivities(self) -> list:
        return list(self._dataframe["SENSNAME"].unique()) if self.sensrun else []

    @property
    def sensrun(self) -> bool:
        return self._sensrun

    @property
    def sens_df(self) -> pd.DataFrame:
        return self.dataframe[self.POSSIBLE_SELECTORS]

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def _prepare_data(
        self, drop_constants: bool = True, keep_numeric_only: bool = True
    ) -> None:
        """
        Different data preparations on the parameters, before storing them as an attribute.
        Option to drop parameters with constant values. Prefixes on parameters from GEN_KW
        are removed, in addition parameters with LOG distribution will be kept while the
        other is dropped.
        """

        if drop_constants:
            constant_params = [
                param
                for param in self._dataframe
                if self._dataframe[param].nunique() == 1
                and param not in self.POSSIBLE_SELECTORS
            ]
            self._dataframe = self._dataframe.drop(columns=constant_params)

        # Keep only LOG parameters
        log_params = [param for param in self._dataframe if param.startswith("LOG10_")]
        self._dataframe = self._dataframe.drop(
            columns=[param.replace("LOG10_", "") for param in log_params]
        )
        self._dataframe = self._dataframe.rename(
            columns={col: f"{col} (log)" for col in log_params}
        )
        # Remove prefix on parameter name added by GEN_KW
        self._dataframe = self._dataframe.rename(
            columns={
                col: (col.split(":", 1)[1]) for col in self._dataframe if ":" in col
            }
        )
        # Drop columns if duplicate names
        self._dataframe = self._dataframe.loc[:, ~self._dataframe.columns.duplicated()]

        # Only use numeric columns
        if keep_numeric_only:
            numeric_columns = self._dataframe.select_dtypes(
                include=np.number
            ).columns.tolist()
            self._dataframe = self._dataframe[
                self.selectors
                + [col for col in numeric_columns if col not in self.selectors]
            ]

    def _check_if_sensitivity_run(self) -> bool:
        """
        Flag ensembles as sensrun if more than one sensitivity exists or
        there exist only one sensitivity which is not of type montecarlo.
        """

        if "SENSNAME" not in self._dataframe:
            return False

        if self.dataframe["SENSNAME"].isnull().values.any():
            raise ValueError(
                "Ensembles with and without sensitivity data mixed - this is not supported!"
            )

        # set senstype from senscase
        mc_mask = self._dataframe["SENSCASE"] == "p10_p90"
        self._dataframe.loc[mc_mask, "SENSTYPE"] = "mc"
        self._dataframe.loc[~mc_mask, "SENSTYPE"] = "scalar"

        return not all(
            (
                (df["SENSNAME"].nunique() == 1 and df["SENSTYPE"].unique() == ["mc"])
                for _, df in self.dataframe.groupby("ENSEMBLE")
            )
        )
