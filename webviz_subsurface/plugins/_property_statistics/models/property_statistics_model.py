from typing import Any, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from webviz_config import WebvizConfigTheme

from webviz_subsurface._figures import create_figure


# pylint: disable=too-many-public-methods
class PropertyStatisticsModel:
    """Class to process and visualize ensemble property statistics data"""

    REQUIRED_COLUMNS = [
        "ENSEMBLE",
        "REAL",
        "SOURCE",
        "ID",
        "PROPERTY",
        "Avg",
        "Avg_Weighted",
        "Max",
        "Min",
        "P10",
        "P90",
        "Stddev",
    ]
    REQUIRED_SELECTORS = ["ZONE"]
    SKIPPED_COLUMNS = ["Count"]

    def __init__(self, dataframe: pd.DataFrame, theme: WebvizConfigTheme) -> None:
        self._dataframe = dataframe
        self._dataframe["REAL"] = self._dataframe["REAL"].astype(int)
        self._prepare_and_validate_data()
        self._dataframe["label"] = self._dataframe.agg(
            lambda x: " | ".join(
                [f"{x[sel]}" for sel in ["PROPERTY"] + self.selectors]
            ),
            axis=1,
        )
        self.theme = theme
        self.colorway = self.theme.plotly_theme.get("layout", {}).get("colorway", None)
        self._statframe = self.aggregate_ensemble_data()

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    def _prepare_and_validate_data(self) -> None:
        for column in self.REQUIRED_COLUMNS + self.REQUIRED_SELECTORS:
            if column not in self.dataframe.columns:
                raise KeyError(
                    f"{column} column is missing from property statistics data"
                )
        self._dataframe = self._dataframe.drop(
            self.SKIPPED_COLUMNS, axis=1, errors="ignore"
        )
        sources = self.dataframe["SOURCE"].unique()
        if len(sources) > 1:
            raise ValueError(
                f"Property statistics data has multiple sources: {sources}. "
                "Only one source is supported"
            )
        ids = self.dataframe["ID"].unique()
        if len(sources) > 1:
            raise ValueError(
                f"Property statistics data has multiple ids: {ids}. "
                "Only one id is supported"
            )

    @property
    def statframe(self) -> pd.DataFrame:
        return self._statframe

    @property
    def selectors(self) -> List[str]:
        """List of user set selectors"""
        return [
            x
            for x in self.dataframe.columns
            if x not in self.REQUIRED_COLUMNS + ["label"]
        ]

    def selector_values(self, selector: str) -> List[Any]:
        return list(self.dataframe[selector].unique())

    def selectors_has_value(self, value: str = "Total") -> bool:
        for selector in self.selectors:
            if value not in self.selector_values(selector):
                return False
        return True

    @property
    def properties(self) -> List[str]:
        return list(self.dataframe["PROPERTY"].unique())

    @property
    def zones(self) -> List[str]:
        return list(self.dataframe["ZONE"].unique())

    @property
    def sources(self) -> List[str]:
        return list(self.dataframe["SOURCE"].unique())

    @property
    def ensembles(self) -> List[str]:
        return list(self.dataframe["ENSEMBLE"].unique())

    def aggregate_ensemble_data(self) -> pd.DataFrame:

        return (
            self.dataframe.drop(columns=["ID", "REAL"], errors="ignore")
            .groupby(["ENSEMBLE", "label", "PROPERTY", "SOURCE"] + self.selectors)[
                "Avg"
            ]
            .agg(
                [
                    ("Avg_Avg", "mean"),
                    ("Avg_P10", lambda x: np.percentile(x, 10)),
                    ("Avg_P90", lambda x: np.percentile(x, 90)),
                    ("Avg_Stddev", "std"),
                ]
            )
            .reset_index()
        )

    def get_labels(self, drop_constants: bool = True) -> List[str]:
        if drop_constants:
            return self.statframe[self.statframe["Avg_Stddev"] > 0]["label"].unique()
        return self.statframe["label"].unique()

    def get_real_order(
        self, ensemble: str, series: str, statistic: str = "Avg"
    ) -> pd.DataFrame:
        df = self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]
        df = df[df["label"] == series]
        return df.sort_values(by=statistic)[[statistic, "REAL"]]

    def filter_on_label(
        self, ensemble: str, label: str, statistic: str = "Avg"
    ) -> pd.Series:
        return self.dataframe[
            (self.dataframe["ENSEMBLE"] == ensemble)
            & (self.dataframe["label"] == label)
        ][statistic]

    @staticmethod
    def filter_dataframe(
        dframe: pd.DataFrame, columns: list, column_values: list
    ) -> pd.DataFrame:

        if not isinstance(columns, list):
            columns = [columns]
        for filt, col in zip(column_values, columns):
            if isinstance(filt, list):
                dframe = dframe.loc[dframe[col].isin(filt)]
            else:
                dframe = dframe.loc[dframe[col] == filt]
        return dframe

    def filter_reals_on_label_range(
        self, ensemble: str, label: str, min_max: list, statistic: str = "Avg"
    ) -> pd.Series:
        return self.dataframe[
            (self.dataframe["ENSEMBLE"] == ensemble)
            & (self.dataframe["label"] == label)
            & (self.dataframe[statistic].between(min_max[0], min_max[1]))
        ]["REAL"]

    def get_ensemble_properties(
        self,
        ensemble: str,
        selector_values: List[Any],
        statistic: str = "Avg",
    ) -> pd.DataFrame:
        df = self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]

        if selector_values is not None:
            df = self.filter_dataframe(df, self.selectors, selector_values)
        df = df[["REAL", statistic, "label"]]
        if df.empty:
            return df
        return (
            df.pivot_table(columns=["label"], values=statistic, index="REAL")
            .rename_axis(None, axis=1)
            .reset_index()
        )

    def delta_statistics(
        self,
        prop: str,
        ensemble: str,
        delta_ensemble: str,
        selector_values: List[Any],
        statistic: str = "Avg",
        aggregation: str = "Avg",
    ) -> pd.DataFrame:

        df = self.statframe.copy()

        if selector_values is not None:
            df = self.filter_dataframe(df, self.selectors, selector_values)
        df = df[df["PROPERTY"] == prop]
        df["label"] = df.agg(
            lambda x: " | ".join([f"{x[sel]}" for sel in self.selectors]), axis=1
        )

        # Drop non-numerical columns before aggregations
        df = df.drop(columns=["SOURCE", "PROPERTY"] + self.selectors)

        df = df[df["ENSEMBLE"].isin([ensemble, delta_ensemble])]
        df = df.pivot_table(columns=["ENSEMBLE"], index="label").reset_index()

        df["diff"] = (
            df[f"{statistic}_{aggregation}"][ensemble]
            - df[f"{statistic}_{aggregation}"][delta_ensemble]
        )
        if aggregation == "Avg":
            df["diff"] = abs(df["diff"])
        df = df.sort_values(by=["diff"])
        return df

    def make_delta_table(
        self,
        prop: str,
        ensemble: str,
        delta_ensemble: str,
        selector_values: List[Any],
        statistic: str = "Avg",
        aggregation: str = "Avg",
    ) -> Tuple[List[Any], List[Any]]:
        df = self.delta_statistics(
            prop=prop,
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            selector_values=selector_values,
            statistic=statistic,
            aggregation=aggregation,
        )
        return self.make_table(df)

    def make_delta_bars(
        self,
        prop: str,
        ensemble: str,
        delta_ensemble: str,
        selector_values: List[Any],
        statistic: str = "Avg",
        aggregation: str = "Avg",
    ) -> go.Figure:
        df = self.delta_statistics(
            prop=prop,
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            selector_values=selector_values,
            statistic=statistic,
            aggregation=aggregation,
        )
        fig = go.Figure(
            data=[
                {
                    "median": df["Avg_Avg"][ensemble],
                    "q1": df["Avg_P10"][ensemble],
                    "q3": df["Avg_P90"][ensemble],
                    "y": df["label"],
                    "type": "box",
                    "name": ensemble,
                    "hovertemplate": "test",
                    "hovertext": "none",
                },
                {
                    "median": df["Avg_Avg"][delta_ensemble],
                    "q1": df["Avg_P10"][delta_ensemble],
                    "q3": df["Avg_P90"][delta_ensemble],
                    "y": df["label"],
                    "type": "box",
                    "name": delta_ensemble,
                    "hovertemplate": "test",
                    "hovertext": "none",
                },
            ]
        )

        # Keep zoom level on click
        fig.update_layout(
            uirevision=f"{ensemble}{delta_ensemble}{prop}{str(df.size)}{aggregation}",
            boxmode="group",
            margin={"t": 20},
            yaxis_type="category",
        )
        fig = fig.to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])
        return fig

    @staticmethod
    def make_table(df: pd.DataFrame) -> Tuple[List[Any], List[Any]]:
        df.columns = df.columns.map("|".join)
        columns = [
            {
                "id": col,
                "name": [col.split("|")[0], col.split("|")[1]],
                "type": "numeric",
                "format": {"specifier": ".3~r"},
            }
            for col in df.columns
        ]
        return columns, df.iloc[::-1].to_dict("records")

    def make_statistics_table(
        self,
        ensembles: list,
        prop: str,
        selector_values: List[Any],
    ) -> Tuple[List[Any], List[Any]]:
        df = self.statframe.copy()
        df = df[df["PROPERTY"] == prop]
        if selector_values is not None:
            df = self.filter_dataframe(df, self.selectors, selector_values)

        # Drop non-numerical columns before aggregations
        df = df.drop(columns=["SOURCE", "PROPERTY"] + self.selectors)
        df = df[df["ENSEMBLE"].isin(ensembles)]
        df = df.pivot_table(columns=["ENSEMBLE"], index="label").reset_index()
        return self.make_table(df)

    def make_grouped_plot(
        self,
        ensembles: list,
        prop: str,
        selector_values: List[Any],
        statistic: str = "Avg",
        plot_type: str = "histogram",
        match_axis: bool = False,
    ) -> go.Figure:
        sel_length = 1
        for selector in selector_values:
            sel_length *= len(selector)

        df = self.dataframe.copy()
        df = df[df["PROPERTY"] == prop]
        if selector_values is not None:
            df = self.filter_dataframe(df, self.selectors, selector_values)

        df = df[df["ENSEMBLE"].isin(ensembles)]

        fig = create_figure(
            plot_type=plot_type if plot_type != "scatter_ensemble" else "scatter",
            data_frame=df,
            x="REAL" if plot_type != "distribution" else statistic,
            y=statistic if plot_type != "distribution" else None,
            facet_col="label" if plot_type != "scatter_ensemble" else "ENSEMBLE",
            color="ENSEMBLE" if plot_type != "scatter_ensemble" else "label",
            color_discrete_sequence=self.colorway,
        )
        if not match_axis:
            fig.update_xaxes(matches=None).update_yaxes(matches=None)

        fig = fig.to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])
        return fig

    def get_real_and_value_df(
        self,
        ensemble: str,
        series: str,
        normalize: bool = False,
        statistic: str = "Avg",
    ) -> pd.DataFrame:
        """
        Return dataframe with label and values for selected label for an ensemble.
        A column with normalized values can be added.
        """
        df = self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]
        df = df[df["label"] == series]
        if normalize:
            df["VALUE_NORM"] = (df[statistic] - df[statistic].min()) / (
                df[statistic].max() - df[statistic].min()
            )

        df.rename(columns={statistic: "VALUE"}, inplace=True)

        return df[["label", "REAL", "VALUE", "VALUE_NORM"]].reset_index(drop=True)
