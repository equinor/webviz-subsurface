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
        "SENSNAME_CASE",
    ]

    def __init__(
        self,
        dataframe: pd.DataFrame,
        drop_constants: bool = True,
        keep_numeric_only: bool = True,
        drop_parameters_with_nan: bool = False,
    ) -> None:
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
        self._validate_dframe()
        self._sensrun = self._check_if_sensitivity_run()
        self._prepare_data(drop_constants, keep_numeric_only, drop_parameters_with_nan)
        self._parameters = [
            x for x in self._dataframe if x not in self.POSSIBLE_SELECTORS
        ]
        self._parameters_per_ensemble = self._split_parameters_by_ensemble()

    @property
    def ensembles(self) -> list:
        return list(self._dataframe["ENSEMBLE"].unique())

    @property
    def parameters(self) -> list:
        return self._parameters

    @property
    def parameters_per_ensemble(self) -> dict:
        return self._parameters_per_ensemble

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
    def sensitivity_ensembles(self) -> list:
        return self._sensitivity_ensembles

    @property
    def mc_ensembles(self) -> list:
        return [ens for ens in self.ensembles if ens not in self._sensitivity_ensembles]

    @property
    def sens_df(self) -> pd.DataFrame:
        return self.dataframe[self.POSSIBLE_SELECTORS]

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def _validate_dframe(self) -> None:
        for col in ["REAL", "ENSEMBLE"]:
            if col not in self._dataframe:
                raise KeyError(f"Required columns {col} not found in dataframe")

    def _prepare_data(
        self,
        drop_constants: bool,
        keep_numeric_only: bool,
        drop_parameters_with_nan: bool,
    ) -> None:
        """
        Different data preparations on the parameters, before storing them as an attribute.
        Option to drop parameters with constant values. Prefixes on parameters from GEN_KW
        are removed, in addition parameters with LOG distribution will be kept while the
        other is dropped.
        """

        # Remove parameters with only NaN (can happen for filtered dataframes)
        self._dataframe = self._dataframe.dropna(axis=1, how="all")

        if drop_constants:
            constant_params = [
                param
                for param in self._dataframe
                if self._dataframe[param].dropna().nunique() == 1
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

        if drop_parameters_with_nan:
            self._dataframe = self._dataframe.drop(columns=self._get_columns_with_nan())

    def _check_if_sensitivity_run(self) -> bool:
        """
        Flag ensembles as sensrun if more than one sensitivity exists or
        there exist only one sensitivity which is not of type montecarlo.
        """
        self._sensitivity_ensembles = []

        if "SENSNAME" not in self._dataframe:
            return False

        # if mix of gen_kw and sensitivity ensembles add
        # dummy sensitivvity columns to gen_kw ensembles
        gen_kw_mask = self._dataframe["SENSNAME"].isnull()
        self._dataframe.loc[gen_kw_mask, "SENSNAME"] = "🎲"
        self._dataframe.loc[gen_kw_mask, "SENSCASE"] = "p10_p90"

        # set senstype from senscase
        mc_mask = self._dataframe["SENSCASE"] == "p10_p90"
        self._dataframe["SENSTYPE"] = np.where(mc_mask, "mc", "scalar")

        # make combination column of sensname and senscase
        self._dataframe["SENSNAME_CASE"] = np.where(
            mc_mask,
            self._dataframe["SENSNAME"],
            self._dataframe[["SENSNAME", "SENSCASE"]].agg("--".join, axis=1),
        )

        self._sensitivity_ensembles = [
            ens
            for ens, df in self.dataframe.groupby("ENSEMBLE")
            if not (df["SENSNAME"].nunique() == 1 and df["SENSTYPE"].unique() == ["mc"])
        ]
        return bool(self._sensitivity_ensembles)

    def _get_columns_with_nan(self) -> list:
        """Return parameters that contains nan values within ensembles"""
        cols_with_nan = []
        for _, ensdf in self._dataframe.groupby("ENSEMBLE"):
            cols_with_nan.extend(
                [
                    col
                    for col in ensdf
                    if ensdf[col].isnull().values.any()
                    and not ensdf[col].isnull().values.all()
                ]
            )
        return cols_with_nan

    def _split_parameters_by_ensemble(self) -> dict:
        return {
            ens: [
                col
                for col in ensdf.dropna(axis=1, how="all").columns
                if col in self._parameters
            ]
            for ens, ensdf in self._dataframe.groupby("ENSEMBLE")
        }

    def get_parameters_for_ensembles(self, ensembles: list) -> list:
        """Get the unique parameters belonging to one or more ensembles"""
        parameters = set()
        for ens in ensembles:
            parameters.update(self._parameters_per_ensemble[ens])
        return sorted(list(parameters))
