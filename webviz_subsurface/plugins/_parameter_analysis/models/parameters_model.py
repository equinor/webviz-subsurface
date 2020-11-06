from typing import List, Tuple, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash_table.Format import Format

# pylint: disable=too-many-public-methods
class ParametersModel:
    """Class to process and visualize ensemble parameter data"""

    REQUIRED_COLUMNS = ["ENSEMBLE", "REAL"]

    def __init__(
        self, dataframe: pd.DataFrame, theme: dict, drop_constants: bool = True
    ) -> None:
        self._dataframe = dataframe
        self.theme = theme
        self.colorway = self.theme.plotly_theme.get("layout", {}).get("colorway", None)
        self._parameters = []
        self._prepare_data(drop_constants)
        self._statframe = self._aggregate_ensemble_data(self._dataframe)
        self._statframe_normalized = self._normalize_and_aggregate()

    @property
    def dataframe_melted(self) -> pd.DataFrame:
        return self.dataframe.melt(
            id_vars=["ENSEMBLE", "REAL"], var_name="PARAMETER", value_name="VALUE"
        )

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def statframe(self) -> pd.DataFrame:
        return self._statframe

    @property
    def parameters(self) -> pd.DataFrame:
        return self._parameters

    @parameters.setter
    def parameters(self, sortorder):
        self._parameters = sortorder

    @property
    def ensembles(self) -> List[str]:
        return list(self.dataframe["ENSEMBLE"].unique())

    def _prepare_data(self, drop_constants):
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

        self._parameters = [
            x for x in self._dataframe.columns if x not in self.REQUIRED_COLUMNS
        ]

    @staticmethod
    def _aggregate_ensemble_data(dframe) -> pd.DataFrame:
        """Compute parameter statistics for the different ensembles"""
        return (
            dframe.drop(columns=["REAL"])
            .groupby(["ENSEMBLE"])
            .agg(
                [
                    ("Avg", np.mean),
                    ("Stddev", np.std),
                    ("P10", lambda x: np.percentile(x, 10)),
                    ("P90", lambda x: np.percentile(x, 90)),
                    ("Min", np.min),
                    ("Max", np.max),
                ]
            )
            .stack(0)
            .rename_axis(["ENSEMBLE", "PARAMETER"])
            .reset_index()
        )

    def _normalize_and_aggregate(self):
        """
        Normalize parameter values to be able to compare distribution updates
        for different parameters
        """
        df = self._dataframe.copy()
        df_norm = (df[self.parameters] - df[self.parameters].min()) / (
            df[self.parameters].max() - df[self.parameters].min()
        )
        df_norm[self.REQUIRED_COLUMNS] = df[self.REQUIRED_COLUMNS]
        df = self._aggregate_ensemble_data(df_norm)
        return df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()

    def sort_parameters(
        self,
        ensemble: str,
        delta_ensemble: str,
        sortby: str,
    ):
        """Sort parameter list from selection"""
        # compute diff between ensembles
        df = self._statframe_normalized.copy()
        df["Avg", "diff"] = abs(df["Avg"][ensemble] - df["Avg"][delta_ensemble])
        df["Stddev", "diff"] = df["Stddev"][ensemble] - df["Stddev"][delta_ensemble]

        # set parameter column and update parameter list
        df = df.sort_values(
            by="PARAMETER" if sortby == "Name" else [(sortby, "diff")],
            ascending=(sortby == "Name"),
        )
        self._parameters = list(df["PARAMETER"])
        return list(df["PARAMETER"])

    @staticmethod
    def make_table(df: pd.DataFrame) -> Tuple[List[Any], List[Any]]:
        """Return format needed for dash table"""
        col_order = ["PARAMETER", "Avg", "Stddev", "P90", "P10", "Min", "Max"]
        df = df.reindex(col_order, axis=1, level=0)
        df.columns = df.columns.map(" | ".join).str.strip(" | ")
        columns = [
            {"id": col, "name": col, "type": "numeric", "format": Format(precision=3)}
            for col in df.columns
        ]
        return columns, df.to_dict("records")

    def _sort_parameters_col(self, df, parameters):
        """Sort parameter column in dataframe"""
        sortorder = [x for x in self._parameters if x in parameters]
        return df.set_index("PARAMETER").loc[sortorder].reset_index()

    def make_statistics_table(
        self,
        ensembles: list,
        parameters: List[Any],
    ) -> Tuple[List[Any], List[Any]]:
        """Create table with statistics for selected parameters"""
        df = self.statframe.copy()
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df[df["PARAMETER"].isin(parameters)]
        df = df.pivot_table(columns=["ENSEMBLE"], index="PARAMETER").reset_index()
        df = self._sort_parameters_col(df, parameters)
        return self.make_table(df)

    def make_grouped_plot(
        self,
        ensembles: list,
        parameters: List[Any],
        plot_type: str = "distribution",
    ) -> go.Figure:
        """Create subplots for selected parameters"""
        df = self.dataframe_melted.copy()
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df[df["PARAMETER"].isin(parameters)]
        df = self._sort_parameters_col(df, parameters)

        if plot_type == "distribution":
            fig = (
                px.violin(
                    df,
                    x="VALUE",
                    facet_col="PARAMETER",
                    facet_col_wrap=min(
                        min(
                            [x for x in range(100) if (x * (x + 1)) >= len(parameters)]
                        ),
                        20,
                    ),
                    color="ENSEMBLE",
                    color_discrete_sequence=self.colorway,
                )
                .update_xaxes(
                    matches=None,
                    fixedrange=True,
                    title=None,
                    showticklabels=(len(parameters) < 20),
                )
                .for_each_trace(
                    lambda t: t.update(
                        hoveron="violins",
                        hoverinfo="name",
                        meanline_visible=True,
                        orientation="h",
                        side="positive",
                        width=3,
                        points=False,
                    )
                )
                .for_each_annotation(
                    lambda a: a.update(
                        hovertext=a.text.split("=")[-1],
                        text=(a.text.split("=")[-1]) if len(parameters) < 40 else "",
                    )
                )
            )

        fig = fig.to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])

        return fig

    def get_real_and_value_df(
        self, ensemble: str, parameter: str, normalize: bool = False
    ) -> pd.DataFrame:
        """
        Return dataframe with ralization and values for selected parameter for an ensemble.
        A column with normalized parameter values can be added.
        """
        df = self.dataframe_melted.copy()
        df = df[["VALUE", "REAL"]].loc[
            (df["ENSEMBLE"] == ensemble) & (df["PARAMETER"] == parameter)
        ]
        if normalize:
            df["VALUE_NORM"] = (df["VALUE"] - df["VALUE"].min()) / (
                df["VALUE"].max() - df["VALUE"].min()
            )
        return df.reset_index()
