from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from webviz_subsurface._figures import create_figure


class MapFigure:
    def __init__(
        self,
        dframe: pd.DataFrame,
        color_by: str,
        colormap: dict,
        faultlinedf: Optional[pd.DataFrame] = None,
    ):
        self.dframe = dframe
        self.color_by = color_by
        self.colormap = colormap
        self.hover_data = ["I", "J", "K"]

        self._figure = self.create_figure()

        if faultlinedf is not None:
            self.add_fault_lines(faultlinedf)

    @property
    def figure(self) -> go.Figure:
        return self._figure

    @property
    def axis_layout(self) -> dict:
        return {
            "title": None,
            "showticklabels": False,
            "showgrid": False,
            "showline": False,
        }

    def create_figure(self) -> go.Figure:
        return (
            create_figure(
                plot_type="scatter",
                data_frame=self.dframe,
                x="X",
                y="Y",
                color=self.color_by
                if self.color_by != "PERMX"
                else np.log10(self.dframe[self.color_by]),
                color_discrete_map=self.colormap,
                xaxis={"constrain": "domain", **self.axis_layout},
                yaxis={"scaleanchor": "x", **self.axis_layout},
                hover_data=[self.color_by] + self.hover_data,
                color_continuous_scale="Viridis",
            )
            .update_traces(marker_size=10, unselected={"marker": {"opacity": 0}})
            .update_coloraxes(showscale=False)
            .update_layout(
                plot_bgcolor="white",
                margin={"t": 10, "b": 10, "l": 0, "r": 0},
                showlegend=False,
            )
        )

    def add_fault_lines(self, faultlinedf: pd.DataFrame) -> None:
        for _fault, faultdf in faultlinedf.groupby("POLY_ID"):
            self._figure.add_trace(
                {
                    "x": faultdf["X_UTME"],
                    "y": faultdf["Y_UTMN"],
                    "mode": "lines",
                    "type": "scatter",
                    "hoverinfo": "none",
                    "showlegend": False,
                    "line": {"color": "grey", "width": 1},
                }
            )
