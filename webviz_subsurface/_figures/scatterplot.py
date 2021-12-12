from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

from .._utils.colors import hex_to_rgba


class ScatterPlot:
    def __init__(
        self,
        df: pd.DataFrame,
        response: str,
        param: str,
        color: str,
        title: str,
        plot_trendline: bool = False,
    ):

        self._figure = (
            px.scatter(
                df[[response, param]],
                x=param,
                y=response,
                trendline="ols"
                if plot_trendline and df[response].nunique() > 1
                else None,
                trendline_color_override="#243746",
            )
            .update_layout(
                margin={
                    "r": 20,
                    "l": 20,
                    "t": 60,
                    "b": 20,
                },
                paper_bgcolor="white",
                plot_bgcolor="white",
                title={"text": title, "x": 0.5},
                xaxis_title=None,
                yaxis_title=None,
            )
            .update_traces(
                marker={
                    "size": 15,
                    "color": hex_to_rgba(color, 0.7),
                    "line": {"width": 1.2, "color": hex_to_rgba(color, 1)},
                }
            )
        )

    @property
    def figure(self) -> Dict[str, Any]:
        return self._figure

    def update_color(self, color: str, opacity: float) -> None:
        """Update color for scatter plot"""
        for trace in self._figure["data"]:
            if trace["mode"] == "markers":
                trace["marker"].update(color=hex_to_rgba(color, opacity))
                trace["marker"]["line"].update(color=hex_to_rgba(color, 1))

    def add_trace(
        self,
        x_values: List[float],
        y_values: List[float],
        mode: str,
        color: str,
        dash: str = "solid",
    ) -> None:
        self._figure.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode=mode,
                line=dict(dash=dash, color=color),
                showlegend=False,
            )
        )

    def add_vertical_line_with_error(
        self, value: float, error: float, xmin: float, xmax: float
    ) -> None:
        self.add_trace([xmin, xmax], [value, value], "lines", "#243746")
        self.add_trace(
            [xmin, xmax],
            [value - error, value - error],
            "lines",
            "#243746",
            dash="dash",
        )
        self.add_trace(
            [xmin, xmax],
            [value + error, value + error],
            "lines",
            "#243746",
            dash="dash",
        )
