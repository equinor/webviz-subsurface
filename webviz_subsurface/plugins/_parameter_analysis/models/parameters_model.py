from typing import Any, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from webviz_subsurface._figures import create_figure
from webviz_subsurface._models.parameter_model import ParametersModel as Pmodel


class ParametersModel:
    """Class to process and visualize ensemble parameter data"""

    REQUIRED_COLUMNS = ["ENSEMBLE", "REAL"]

    def __init__(
        self, dataframe: pd.DataFrame, theme: dict, drop_constants: bool = True
    ) -> None:
        self.pmodel = Pmodel(
            dataframe=dataframe, drop_constants=drop_constants, keep_numeric_only=True
        )
        self._dataframe = self.pmodel.dataframe
        self._dataframe["REAL"] = self._dataframe["REAL"].astype(int)
        self._parameters = self.pmodel.parameters
        self.theme = theme
        self.colorway = self.theme.plotly_theme.get("layout", {}).get("colorway", None)
        self._statframe = self._aggregate_ensemble_data(self._dataframe)
        self._statframe_normalized = self._normalize_and_aggregate()
        self._dataframe_melted = self.dataframe.melt(
            id_vars=["ENSEMBLE", "REAL"], var_name="PARAMETER", value_name="VALUE"
        )

    @property
    def dataframe_melted(self) -> pd.DataFrame:
        return self._dataframe_melted

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def statframe(self) -> pd.DataFrame:
        return self._statframe

    @property
    def mc_ensembles(self) -> pd.DataFrame:
        return self.pmodel.mc_ensembles

    @property
    def parameters(self) -> pd.DataFrame:
        return self._parameters

    @parameters.setter
    def parameters(self, sortorder):
        self._parameters = sortorder

    @property
    def ensembles(self) -> List[str]:
        return list(self.dataframe["ENSEMBLE"].unique())

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
        df.columns = df.columns.map("|".join)
        columns = [
            {
                "id": col,
                "name": [col.split("|")[0], col.split("|")[1]],
                "type": "numeric",
                "format": {"specifier": ".5~r"},
            }
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

        return (
            create_figure(
                plot_type=plot_type,
                data_frame=df,
                x="VALUE",
                facet_col="PARAMETER",
                color="ENSEMBLE",
                color_discrete_sequence=self.colorway,
            )
            .update_xaxes(matches=None)
            .for_each_trace(
                lambda t: t.update(
                    text=t["text"].replace("VALUE", "")
                    if t["text"] is not None
                    else None
                )
            )
        )

    def get_stat_value(self, parameter: str, ensemble: str, stat_column: str):
        """
        Retrive statistical value for a parameter in an ensamble.
        """
        return self.statframe.loc[
            (self.statframe["PARAMETER"] == parameter)
            & (self.statframe["ENSEMBLE"] == ensemble)
        ].iloc[0][stat_column]

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
        return df.reset_index(drop=True)

    def get_parameter_df_for_ensemble(self, ensemble: str, reals: list):
        return self._dataframe[
            (self._dataframe["ENSEMBLE"] == ensemble)
            & (self._dataframe["REAL"].isin(reals))
        ]
