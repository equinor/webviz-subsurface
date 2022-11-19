import datetime
from enum import Enum
from typing import List, Optional

import numpy as np
import pandas as pd

from webviz_subsurface._utils.colors import find_intermediate_color, rgba_to_str
from webviz_subsurface._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
)


class Colors(str, Enum):
    RED = rgba_to_str((255, 18, 67, 1))
    MID = rgba_to_str((220, 220, 220, 1))
    GREEN = rgba_to_str((62, 208, 62, 1))


class TimeSeriesFigure:
    STAT_OPTIONS = ["Mean", "P10", "P90"]
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        dframe: pd.DataFrame,
        visualization: str,
        vector: str,
        ensemble: str,
        color_col: str,
        line_shape_fallback: str,
        historical_vector_df: Optional[pd.DataFrame] = None,
        dateline: Optional[datetime.datetime] = None,
    ):
        self.dframe = dframe
        self.vector = vector
        self.ensemble = ensemble
        self.color_col = color_col
        self.visualization = visualization
        self.historical_vector_df = historical_vector_df
        self.date = dateline
        self.line_shape = self.get_line_shape(line_shape_fallback)

        self.create_traces()

    @property
    def figure(self) -> dict:
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
                "title": {"text": f"{self.vector} colored by {self.color_col}"},
                "shapes": self.shapes,
                "annotations": self.annotations,
            },
        }

    def create_traces(self) -> None:
        self.traces: List[dict] = []

        if self.visualization != "statistics":
            self._add_realization_traces()

        if self.visualization != "realizations":
            self._add_statistic_traces()

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

    def _add_statistic_traces(self) -> None:
        """Renders the statistic lines"""
        stat_df = self.create_vectors_statistics_df()
        stat_df = pd.DataFrame(stat_df["DATE"]).join(stat_df[self.vector])
        self.traces.extend(
            [
                {
                    "line": {
                        "width": 2,
                        "shape": self.line_shape,
                        "dash": False if stat == "Mean" else "dashdot",
                        "color": Colors.RED,
                    },
                    "mode": "lines",
                    "x": stat_df["DATE"],
                    "y": stat_df[stat],
                    "name": stat,
                    "legendgroup": self.ensemble,
                    "showlegend": False,
                }
                for stat in self.STAT_OPTIONS
            ]
        )

    def _add_realization_traces(self) -> None:
        """Renders line trace for each realization"""
        mean = self.dframe["VALUE_NORM"].mean()
        self.traces.extend(
            [
                {
                    "line": {
                        "shape": self.line_shape,
                        "color": self.set_real_color(
                            real_df["VALUE_NORM"].iloc[0], mean
                        )
                        if self.visualization == "realizations"
                        else "gainsboro",
                    },
                    "mode": "lines",
                    "x": real_df["DATE"],
                    "y": real_df[self.vector],
                    "name": self.ensemble,
                    "legendgroup": self.ensemble,
                    "hovertext": self.create_hovertext(real_df["VALUE"].iloc[0], real),
                    "showlegend": real_idx == 0,
                }
                for real_idx, (real, real_df) in enumerate(self.dframe.groupby("REAL"))
            ]
        )

    @property
    def daterange(self) -> list:
        active_dates = self.dframe["DATE"][self.dframe[self.vector] != 0]
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
