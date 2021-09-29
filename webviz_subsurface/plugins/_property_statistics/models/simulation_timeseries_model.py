from typing import Optional, Union

import pandas as pd
from webviz_config import WebvizConfigTheme
from webviz_config.common_cache import CACHE

from webviz_subsurface._abbreviations.reservoir_simulation import (
    historical_vector,
    simulation_vector_description,
)
from webviz_subsurface._utils.colors import hex_to_rgba
from webviz_subsurface._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
)


class SimulationTimeSeriesModel:
    """Class to process and and visualize ensemble timeseries"""

    def __init__(
        self,
        dataframe: pd.DataFrame,
        theme: WebvizConfigTheme,
        metadata: Optional[pd.DataFrame] = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        for column in ["ENSEMBLE", "REAL", "DATE"]:
            if column not in dataframe.columns:
                raise KeyError(f"{column} column is missing from UNSMRY data")

        self._dataframe = dataframe
        self.theme = theme

        self._metadata = metadata
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )

        # Currently we cannot be sure what data type the DATE column has.
        # Apparently it will have datetime if the source is SMRY files, but
        # may be of type str if the source is CSV files.
        # Try and detect if the data type is string by sampling the first entry
        sample_date = self._dataframe["DATE"].iloc[0]
        self._date_column_is_str = isinstance(sample_date, str)

    @property
    def colors(self) -> dict:
        try:
            return self.theme.plotly_theme["layout"]["colorway"]
        except KeyError:
            return self.theme.plotly_theme.get(
                "colorway",
                [
                    "#243746",
                    "#eb0036",
                    "#919ba2",
                    "#7d0023",
                    "#66737d",
                    "#4c9ba1",
                    "#a44c65",
                    "#80b7bc",
                    "#ff1243",
                    "#919ba2",
                    "#be8091",
                    "#b2d4d7",
                    "#ff597b",
                    "#bdc3c7",
                    "#d8b2bd",
                    "#ffe7d6",
                    "#d5eaf4",
                    "#ff88a1",
                ],
            )

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @property
    def metadata(self) -> pd.DataFrame:
        return self._metadata

    @property
    def vectors(self) -> list:
        return [
            c
            for c in self.dataframe.columns
            if c not in ["REAL", "ENSEMBLE", "DATE"]
            and not historical_vector(c, self.metadata, False) in self.dataframe.columns
        ]

    @property
    def ens_colors(self) -> dict:
        return {ens: self.colors[self.ensembles.index(ens)] for ens in self.ensembles}

    @property
    def dropdown_options(self) -> list:
        return [
            {"label": f"{simulation_vector_description(vec)} ({vec})", "value": vec}
            for vec in self.vectors
        ]

    @property
    def ensembles(self) -> list:
        return list(self.dataframe["ENSEMBLE"].unique())

    def get_line_shape(self, vector: str) -> str:
        return get_simulation_line_shape(
            line_shape_fallback=self.line_shape_fallback,
            vector=vector,
            smry_meta=self.metadata,
        )

    def get_ensemble_vector_for_date(
        self, ensemble: str, vector: str, date: str
    ) -> pd.DataFrame:
        # If the data type of the DATE column is string, use the passed date argument
        # directly. Otherwise convert to datetime before doing query
        query_date = date if self._date_column_is_str else pd.to_datetime(date)

        df = self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]
        df = df.loc[df["DATE"] == query_date]
        return df[[vector, "REAL"]]

    def get_last_date(self, ensemble: str) -> str:
        return str(self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]["DATE"].max())

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def add_statistic_traces(self, ensembles: list, vector: str) -> list:
        """Calculate statistics for a given vector for relevant ensembles"""
        quantiles = [10, 90]
        traces = []
        ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
        dataframe = self.dataframe[self.dataframe["ENSEMBLE"].isin(ensembles)]
        for ensemble, ens_df in dataframe.groupby("ENSEMBLE"):
            dframe = ens_df.drop(columns=["ENSEMBLE", "REAL"]).groupby("DATE")

            # Build a dictionary of dataframes to be concatenated
            dframes = {}
            dframes["mean"] = dframe.mean()
            for quantile in quantiles:
                quantile_str = "p" + str(quantile)
                dframes[quantile_str] = dframe.quantile(q=quantile / 100.0)
            dframes["maximum"] = dframe.max()
            dframes["minimum"] = dframe.min()
            traces.extend(
                add_fanchart_traces(
                    pd.concat(dframes, names=["STATISTIC"], sort=False)[vector],
                    self.ens_colors.get(
                        ensemble, self.ens_colors[list(self.ens_colors.keys())[0]]
                    ),
                    ensemble,
                    self.get_line_shape(vector),
                )
            )

        historical_vector_name = historical_vector(
            vector=vector, smry_meta=self.metadata
        )
        if historical_vector_name and historical_vector_name in dataframe.columns:
            traces.append(self.add_history_trace(dataframe, historical_vector_name))
        return traces

    def add_history_trace(self, dframe: pd.DataFrame, vector: str) -> dict:
        """Renders the history line"""
        df = dframe.loc[
            (dframe["REAL"] == dframe["REAL"].unique()[0])
            & (dframe["ENSEMBLE"] == dframe["ENSEMBLE"].unique()[0])
        ]
        return {
            "line": {"shape": self.get_line_shape(vector)},
            "x": df["DATE"].astype(str),
            "y": df[vector],
            "hovertext": "History",
            "hoverinfo": "y+x+text",
            "name": "History",
            "marker": {"color": "black"},
            "showlegend": True,
        }

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def add_ensset_realization_traces(
        self, ensembles: Union[str, list], vector: str
    ) -> list:
        """Renders line trace for each realization grouped by ensemble,
        includes history line if present"""
        ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
        dataframe = self.dataframe[self.dataframe["ENSEMBLE"].isin(ensembles)]
        traces = [
            {
                "line": {"shape": self.get_line_shape(vector)},
                "x": list(real_df["DATE"].astype(str)),
                "y": list(real_df[vector]),
                "hovertext": f"Realization: {real}, Ensemble: {ensemble}",
                "name": ensemble,
                "legendgroup": ensemble,
                "marker": {
                    "color": self.ens_colors.get(
                        ensemble, self.ens_colors[list(self.ens_colors.keys())[0]]
                    )
                },
                "showlegend": real_idx == 0,
            }
            for ens_no, (ensemble, ens_df) in enumerate(dataframe.groupby("ENSEMBLE"))
            for real_idx, (real, real_df) in enumerate(ens_df.groupby("REAL"))
        ]

        historical_vector_name = historical_vector(
            vector=vector, smry_meta=self.metadata
        )
        if historical_vector_name and historical_vector_name in dataframe.columns:
            traces.append(self.add_history_trace(dataframe, historical_vector_name))
        return traces

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def add_realization_traces(
        self, ensemble: str, vector: str, real_filter: pd.Series = None
    ) -> list:
        """Renders line trace for each realization, includes history line if present"""
        dataframe = self.dataframe[self.dataframe["ENSEMBLE"] == ensemble]
        dataframe = (
            dataframe[dataframe["REAL"].isin(real_filter)]
            if real_filter is not None
            else dataframe
        )
        traces = [
            {
                "line": {"shape": self.get_line_shape(vector)},
                "x": list(real_df["DATE"].astype(str)),
                "y": list(real_df[vector]),
                "hoverinfo": "skip",
                "name": ensemble,
                "customdata": real,
                "legendgroup": ensemble,
                "marker": {"color": "red"},
                "showlegend": real_idx == 0,
            }
            for real_idx, (real, real_df) in enumerate(dataframe.groupby("REAL"))
        ]

        historical_vector_name = historical_vector(
            vector=vector, smry_meta=self.metadata
        )
        if historical_vector_name and historical_vector_name in dataframe.columns:
            traces.append(self.add_history_trace(dataframe, historical_vector_name))
        return traces


def add_fanchart_traces(
    vector_stats: pd.DataFrame, color: str, legend_group: str, line_shape: str
) -> list:
    """Renders a fanchart for an ensemble vector"""

    fill_color = hex_to_rgba(color, 0.3)
    line_color = hex_to_rgba(color, 1)
    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "x": vector_stats["maximum"].index.tolist(),
            "y": vector_stats["maximum"].values,
            "mode": "lines",
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10",
            "x": vector_stats["p10"].index.tolist(),
            "y": vector_stats["p10"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "x": vector_stats["mean"].index.tolist(),
            "y": vector_stats["mean"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "P90",
            "x": vector_stats["p90"].index.tolist(),
            "y": vector_stats["p90"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "x": vector_stats["minimum"].index.tolist(),
            "y": vector_stats["minimum"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color, "shape": line_shape},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]
