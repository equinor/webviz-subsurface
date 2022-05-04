from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objs as go

from .._utils.colors import hex_to_rgba_str
from .px_figure import create_figure


class ScatterPlot:
    """Class to create a general scatterplot

    Input:
    * df: dataframe with values
    * response: y-axis parameter
    * param: x-axis parameter
    * color: marker color
    * title
    * plot_trendline (default False)
    """

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
            create_figure(
                plot_type="scatter",
                data_frame=df[["REAL", response, param]],
                x=param,
                y=response,
                trendline="ols"
                if plot_trendline and df[response].nunique() > 1
                else None,
                trendline_color_override="#243746",
                hover_data=["REAL", response, param],
                framed=False,
            )
            .update_layout(
                margin={"r": 20, "l": 20, "t": 60, "b": 20},
                title={"text": title, "x": 0.5},
                xaxis_title=None,
                yaxis_title=None,
            )
            .update_traces(marker_color=color)
        )

    @property
    def figure(self) -> Dict[str, Any]:
        return self._figure

    def update_color(self, color: str, opacity: float) -> None:
        """Update color for scatter plot"""
        for trace in self._figure["data"]:
            if trace["mode"] == "markers":
                trace["marker"].update(color=hex_to_rgba_str(color, opacity))
                trace["marker"]["line"].update(color=hex_to_rgba_str(color, 1))

    def add_trace(
        self,
        x_values: List[float],
        y_values: List[float],
        mode: str,
        color: str,
        text: str,
        dash: str = "solid",
        showlegend: bool = False,
    ) -> None:
        self._figure.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode=mode,
                line=dict(dash=dash, color=color),
                showlegend=showlegend,
                hovertext=text,
                name=text,
            )
        )

    def add_vertical_line_with_error(
        self, value: float, error: float, xmin: float, xmax: float
    ) -> None:
        self.add_trace(
            [xmin, xmax],
            [value, value],
            "lines",
            "#243746",
            "Observation",
            showlegend=True,
        )
        self.add_trace(
            [xmin, xmax],
            [value - error, value - error],
            "lines",
            "#243746",
            "Observation Error",
            dash="dash",
        )
        self.add_trace(
            [xmin, xmax],
            [value + error, value + error],
            "lines",
            "#243746",
            "Observation Error",
            dash="dash",
        )
        self._figure.update_layout(legend=dict(orientation="h"))
