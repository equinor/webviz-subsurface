import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from webviz_subsurface._utils.colors import (
    find_intermediate_color,
    hex_to_rgb,
    rgb_to_str,
    rgba_to_str,
    scale_rgb_lightness,
)
from webviz_subsurface._utils.enum_shim import StrEnum
from webviz_subsurface._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
)


class Colors(StrEnum):
    RED = rgba_to_str((255, 18, 67, 1))
    MID = rgba_to_str((220, 220, 220, 1))
    GREEN = rgba_to_str((62, 208, 62, 1))


class OneByOneTimeSeriesFigure:
    STAT_OPTIONS = ["Mean", "P10", "P90"]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        dframe: pd.DataFrame,
        visualization: str,
        vector: str,
        ensemble: str,
        color_col: Optional[str],
        line_shape_fallback: str,
        observations: Optional[Dict] = None,
        historical_vector_df: Optional[pd.DataFrame] = None,
        dateline: Optional[datetime.datetime] = None,
        discrete_color_map: Optional[Dict] = None,
        groupby: Optional[str] = None,
    ):
        self.dframe = dframe
        self.color_col = color_col
        self.groupby = groupby
        if color_col is not None and discrete_color_map is None:
            self.dframe = self.normalize_parameter_value(self.dframe)
            self.dframe = self.dframe.rename(columns={color_col: "VALUE"})
        self.vector = vector
        self.ensemble = ensemble
        self.visualization = visualization
        self.historical_vector_df = historical_vector_df
        self.date = dateline
        self.observations = observations if observations is not None else {}
        self.line_shape = self.get_line_shape(line_shape_fallback)
        self.continous_color = self.color_col is not None and discrete_color_map is None
        self.colormap = discrete_color_map if discrete_color_map is not None else {}

        self.create_traces()

        if self.observations:
            self.create_vector_observation_traces()

    @property
    def figure(self) -> dict:
        title = self.vector
        if self.color_col is not None:
            title = f"{title} colored by {self.color_col}"
        return {
            "data": self.traces,
            "layout": {
                "margin": {"r": 40, "l": 20, "t": 60, "b": 20},
                "yaxis": {"automargin": True, "gridcolor": "#ECECEC"},
                "xaxis": {"range": self.daterange, "gridcolor": "#ECECEC"},
                "hovermode": "closest",
                "paper_bgcolor": "white",
                "plot_bgcolor": "white",
                "showlegend": False,
                "uirevision": self.vector,
                "title": {"text": title},
                "shapes": self.shapes,
                "annotations": self.annotations,
            },
        }

    def create_traces(self) -> None:
        self.traces: List[dict] = []

        if self.visualization == "realizations":
            self._add_sensitivity_traces_real()
        else:
            self._add_sensitivity_traces_stat()

        self._add_history_trace()

    def _add_history_trace(self) -> None:
        """Renders the history line"""
        if self.historical_vector_df is None:
            return

        self.traces.append(
            {
                "line": {"shape": self.line_shape, "color": "black"},
                "x": self.historical_vector_df["DATE"],
                "y": self.historical_vector_df[self.vector],
                "mode": "lines",
                "hovertext": "History",
                "hoverinfo": "y+x+text",
                "name": "History",
            }
        )

    @property
    def daterange(self) -> list:
        active_dates = self.dframe["DATE"][self.dframe[self.vector].round(4) != 0]
        if len(active_dates) == 0:
            return [self.dframe["DATE"].min(), self.dframe["DATE"].max()]
        if self.date is None:
            return [active_dates.min(), active_dates.max()]
        # Ensure xaxis covers selected date
        return [min(active_dates.min(), self.date), max(active_dates.max(), self.date)]

    @property
    def annotations(self) -> List[dict]:
        return (
            [
                {
                    "bgcolor": "white",
                    "showarrow": False,
                    "text": self.date.strftime("%Y-%m-%d"),
                    "x": self.date,
                    "y": 1,
                    "yref": "y domain",
                }
            ]
            if self.date is not None
            else []
        )

    @property
    def shapes(self) -> List[dict]:
        return (
            [
                {
                    "line": {"color": "#243746", "dash": "dot", "width": 4},
                    "type": "line",
                    "x0": self.date,
                    "x1": self.date,
                    "xref": "x",
                    "y0": 0,
                    "y1": 1,
                    "yref": "y domain",
                }
            ]
            if self.date is not None
            else []
        )

    def create_hovertext(self, color_value: float, real: int) -> str:
        return f"Real: {real}, {self.color_col}: {color_value}"

    def get_line_shape(self, line_shape_fallback: str) -> str:
        return get_simulation_line_shape(
            line_shape_fallback=set_simulation_line_shape_fallback(line_shape_fallback),
            vector=self.vector,
            smry_meta=None,
        )

    def create_vectors_statistics_df(self) -> pd.DataFrame:
        return (
            self.dframe[["DATE", self.vector]]
            .groupby(["DATE"])
            .agg(
                [
                    ("Mean", np.nanmean),
                    ("P10", lambda x: np.nanpercentile(x, q=90)),
                    ("P90", lambda x: np.nanpercentile(x, q=10)),
                ]
            )
            .reset_index()
        )

    def create_vector_observation_traces(self) -> None:
        """Adds observations to the plot"""

        legend_group = "Observation"
        name = "Observation"
        color = "black"
        show_legend = False

        for observation in self.observations.get("observations", []):
            hovertext = observation.get("comment")
            hovertemplate = (
                "(%{x}, %{y})<br>" + hovertext if hovertext else "(%{x}, %{y})<br>"
            )
            self.traces.append(
                {
                    "name": name,
                    "legendgroup": legend_group,
                    "x": [observation.get("date"), []],
                    "y": [observation.get("value"), []],
                    "marker": {"color": color},
                    "hovertemplate": hovertemplate,
                    "showlegend": show_legend,
                    "error_y": {
                        "type": "data",
                        "array": [observation.get("error"), []],
                        "visible": True,
                    },
                }
            )

    def _add_sensitivity_traces_stat(self) -> None:
        """Renders line trace for each realization"""

        self.dframe["dash"] = np.where(
            self.dframe["SENSCASEID"] == 1, "dashdot", "solid"
        )  # dot, dashdot

        self.traces.extend(
            [
                {
                    "line": {
                        "dash": "dash"
                        if real_df["SENSCASEID"].iloc[0] == 1
                        else "solid",
                        "shape": self.line_shape,
                        "color": self.colormap.get(
                            real_df[self.color_col].iloc[0], "grey"
                        ),
                        "width": 3 if real_df["SENSCASEID"].iloc[0] == 1 else 2,
                    },
                    "mode": "lines",
                    "x": real_df["DATE"],
                    "y": real_df[self.vector],
                    "name": sens,
                    "legendgroup": sens,
                    "hovertext": f"Sens: {sens}",
                }
                for real_idx, (sens, real_df) in enumerate(
                    self.dframe.groupby("SENSNAME_CASE")
                )
            ]
        )

    def _add_sensitivity_traces_real(self) -> None:
        """Renders line trace for each realization"""

        self.dframe["dash"] = np.where(
            self.dframe["SENSCASEID"] == 1, "longdash", "solid"
        )  # dot, dashdot

        self.traces.extend(
            [
                {
                    "line": {
                        "dash": "dash"
                        if real_df["SENSCASEID"].iloc[0] == 1
                        else "solid",
                        "shape": self.line_shape,
                        "color": rgb_to_str(
                            scale_rgb_lightness(
                                hex_to_rgb(
                                    self.colormap.get(
                                        real_df[self.color_col].iloc[0], "grey"
                                    )
                                ),
                                130 if real_df["SENSCASEID"].iloc[0] == 1 else 90,
                            )
                        ),
                        "width": 3 if real_df["SENSCASEID"].iloc[0] == 1 else 2,
                    },
                    "mode": "lines",
                    "x": real_df["DATE"],
                    "y": real_df[self.vector],
                    "name": sens,
                    "legendgroup": sens,
                    "hovertext": f"Real: {real}, Sens: {sens}",
                    "showlegend": real_idx == 0,
                }
                for real_idx, ((sens, real), real_df) in enumerate(
                    self.dframe.groupby(["SENSNAME_CASE", "REAL"])
                )
            ]
        )

    def normalize_parameter_value(self, df: pd.DataFrame) -> pd.DataFrame:
        df["VALUE_NORM"] = (df[self.color_col] - df[self.color_col].min()) / (
            df[self.color_col].max() - df[self.color_col].min()
        )
        return df

    @staticmethod
    def set_real_color(norm_value: float, mean_param_value: float) -> str:
        """
        Return color for trace based on normalized color_col value.
        Midpoint for the colorscale is set on the average value
        """

        if norm_value <= mean_param_value:
            intermed = norm_value / mean_param_value
            return find_intermediate_color(Colors.RED, Colors.MID, intermed)

        if norm_value > mean_param_value:
            intermed = (norm_value - mean_param_value) / (1 - mean_param_value)
            return find_intermediate_color(Colors.MID, Colors.GREEN, intermed)

        return Colors.MID
