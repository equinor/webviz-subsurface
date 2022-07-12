from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...._datainput.fmu_input import scratch_ensemble
from .._plugin_ids import PlugInIDs
from ..view_elements import Graph


class ScatterPlot(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SCATTERPLOT = "scatterplot"

    def __init__(
        self, ensembles: dict, p_cols: List, webviz_settings: WebvizSettings
    ) -> None:
        super().__init__("Scatter plot")

        self.ensembles = ensembles
        self.p_cols = p_cols
        self.plotly_theme = webviz_settings.theme.plotly_theme

        column = self.add_column()
        first_row = column.make_row()
        first_row.add_view_element(Graph(), ScatterPlot.IDs.SCATTERPLOT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ScatterPlot.IDs.SCATTERPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.PARAMETER), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.ENSEMBLE), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Vertical.PARAMETER), "data"
            ),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Vertical.ENSEMBLE), "data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Options.COLOR_BY), "data"),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Options.SHOW_SCATTER), "data"
            ),
        )
        def _update_scatter(
            hor_ens: str,
            hor_param: str,
            ver_ens: str,
            ver_param: str,
            color_by: Union[str, None],
            scatter: List[str],
        ):
            return render_scatter(
                hor_ens,
                hor_param,
                ver_ens,
                ver_param,
                color_by,
                scatter,
                self.plotly_theme,
            )


def render_scatter(
    ens1: str,
    x_col: str,
    ens2: str,
    y_col: str,
    color: Union[str, None],
    density: bool,
    theme: dict,
) -> dict:
    if ens1 == ens2:
        real_text = [f"Realization:{r}" for r in get_parameters(ens1)["REAL"]]
    else:
        real_text = [f"Realization:{r}(x)" for r in get_parameters(ens2)["REAL"]]

    x = get_parameters(ens1)[x_col]
    y = get_parameters(ens2)[y_col]
    color = get_parameters(ens1)[color] if color else None
    data = []
    data.append(
        {
            "x": x,
            "y": y,
            "marker": {"color": color},
            "text": real_text,
            "type": "scatter",
            "mode": "markers",
            "showlegend": False,
        }
    )
    data.append({"x": x, "type": "histogram", "yaxis": "y2", "showlegend": False})
    data.append({"y": y, "type": "histogram", "xaxis": "x2", "showlegend": False})
    if density:
        data.append(
            {
                "x": x,
                "y": y,
                "hoverinfo": "none",
                "autocolorscale": False,
                "showlegend": False,
                "colorscale": [
                    [0, "rgb(255,255,255)"],
                    [0.125, "rgb(37, 52, 148)"],
                    [0.25, "rgb(34, 94, 168)"],
                    [0.375, "rgb(29, 145, 192)"],
                    [0.5, "rgb(65, 182, 196)"],
                    [0.625, "rgb(127, 205, 187)"],
                    [0.75, "rgb(199, 233, 180)"],
                    [0.875, "rgb(237, 248, 217)"],
                    [1, "rgb(255, 255, 217)"],
                ],
                "contours": {
                    "coloring": "fill",
                    "showlines": True,
                    "size": 5,
                    "start": 5,
                },
                "name": "density",
                "ncontours": 20,
                "reversescale": False,
                "showscale": False,
                "type": "histogram2dcontour",
            }
        )
    layout = theme_layout(
        theme,
        {
            "margin": {"t": 20, "b": 100, "l": 100, "r": 10},
            "bargap": 0.05,
            "xaxis": {
                "title": x_col,
                "domain": [0, 0.85],
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showlegend": False,
            },
            "xaxis2": {
                "domain": [0.85, 1],
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showticklabels": False,
            },
            "yaxis": {
                "title": y_col,
                "domain": [0, 0.85],
                "showgrid": False,
                "zeroline": False,
            },
            "yaxis2": {
                "domain": [0.85, 1],
                "showgrid": False,
                "zeroline": False,
                "showticklabels": False,
                "showline": False,
            },
        },
    )

    return {"data": data, "layout": layout}


def get_parameters(ensemble_path: Path) -> pd.DataFrame:
    return (
        scratch_ensemble("", ensemble_path)
        .parameters.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all", axis="columns")
    )


def theme_layout(theme: dict, specific_layout: dict) -> dict:
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout
