from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd
from dash import Input, Output, callback, callback_context
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config.webviz_store import webvizstore

from ...._datainput.fmu_input import scratch_ensemble
from .._plugin_ids import PlugInIDs
from ..view_elements import Graph


class ParameterPlot(ViewABC):
    """Class for the two view elements in the Parameter
    Correlation plugin"""

    class IDs:
        # pylint: disable=too-few-public-methods
        MATRIXPLOT = "matrixplot"
        SCATTERPLOT = "scatterplot"
        MAIN_COLUMN = "main-column"
        MATRIX_ROW = "matrix-row"
        SCATTER_ROW = "scatter-row"

    def __init__(
        self,
        ensembles: dict,
        p_cols: List,
        webviz_settings: WebvizSettings,
        drop_constants: bool = True,
    ) -> None:
        super().__init__("Parameter Correlation")

        self.ensembles = ensembles
        self.p_cols = p_cols
        try:
            self.plotly_theme = webviz_settings.theme.plotly_theme
        except AttributeError:
            print("Attribute error: 'Dash' has no attribute 'theme'")
        self.drop_constants = drop_constants

        column = self.add_column(ParameterPlot.IDs.MAIN_COLUMN)

        first_row = column.make_row(ParameterPlot.IDs.MATRIX_ROW)
        first_row.add_view_element(
            Graph(self.p_cols, matrix=True), ParameterPlot.IDs.MATRIXPLOT
        )

        second_row = column.make_row(ParameterPlot.IDs.SCATTER_ROW)
        second_row.add_view_element(Graph(self.p_cols), ParameterPlot.IDs.SCATTERPLOT)

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Data.CLICK_DATA), "data"),
            Input(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _set_clickdata(cell_data: dict) -> dict:
            return cell_data

        @callback(
            Output(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.BothPlots.ENSEMBLE), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.PARAMETER), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Vertical.PARAMETER), "data"
            ),
            Input(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _update_matrix(
            both_ensemble: str,
            horizontal_paramter: str,
            vertical_parameter: str,
            cell_data: dict,
        ) -> dict:
            """Renders correlation matrix.
            Currently also re-renders matrix to update currently
            selected cell. This is not optimal, but hard to prevent
            as an Output object only can have one callback attached,
            and it is not possible to assign callbacks to individual
            elements of a Plotly graph object
            """
            fig = render_matrix(
                both_ensemble,
                theme=self.plotly_theme,
                drop_constants=self.drop_constants,
            )
            # Finds index of the currently selected cell
            if (
                not callback_context.triggered_id
                == self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string()
                or cell_data is None
            ):
                x_index = list(fig["data"][0]["x"]).index(horizontal_paramter)
                y_index = list(fig["data"][0]["y"]).index(vertical_parameter)
            else:
                horizontal_paramter = cell_data["points"][0]["x"]
                vertical_parameter = cell_data["points"][0]["y"]
                x_index = list(fig["data"][0]["x"]).index(horizontal_paramter)
                y_index = list(fig["data"][0]["y"]).index(vertical_parameter)

            # Adds a shape to highlight the selected cell
            shape = [
                {
                    "xref": "x",
                    "yref": "y",
                    "x0": x_index - 0.5,
                    "y0": y_index - 0.5,
                    "x1": x_index + 0.5,
                    "y1": y_index + 0.5,
                    "type": "rect",
                    "line": {"color": "black"},
                }
            ]
            fig["layout"]["shapes"] = shape

            return fig

        @callback(
            Output(
                self.view_element(ParameterPlot.IDs.SCATTERPLOT)
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
            Input(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _update_scatter(
            horizontal_paramter: str,
            horizontal_ensemble: str,
            vertical_parameter: str,
            vertical_ensemble: str,
            color_by: Union[str, None],
            scatter: List[str],
            cell_data: dict,
        ) -> dict:
            if (
                not callback_context.triggered_id
                == self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string()
                or cell_data is None
            ):
                return render_scatter(
                    horizontal_ensemble,
                    horizontal_paramter,
                    vertical_ensemble,
                    vertical_parameter,
                    color_by,
                    scatter,
                    self.plotly_theme,
                )
            horizontal_paramter = cell_data["points"][0]["x"]
            vertical_parameter = cell_data["points"][0]["y"]
            return render_scatter(
                horizontal_ensemble,
                horizontal_paramter,
                vertical_ensemble,
                vertical_parameter,
                color_by,
                scatter,
                self.plotly_theme,
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(ensemble_path: str, theme: dict, drop_constants: bool = True) -> dict:
    corrdf = get_corr_data(ensemble_path, drop_constants)
    corrdf = corrdf.mask(np.tril(np.ones(corrdf.shape)).astype(np.bool_))

    data = {
        "type": "heatmap",
        "x": corrdf.columns,
        "y": corrdf.columns,
        "z": list(corrdf.values),
        "zmin": -1,
        "zmax": 1,
        "colorscale": theme["layout"]["colorscale"]["sequential"],
    }
    layout = theme_layout(
        theme,
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {"t": 50, "b": 50},
            "xaxis": {
                "ticks": "",
                "showticklabels": False,
                "showgrid": False,
            },
            "yaxis": {
                "ticks": "",
                "showticklabels": False,
                "showgrid": False,
            },
        },
    )

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
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


def theme_layout(theme: dict, specific_layout: dict) -> dict:
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_corr_data(ensemble_path: str, drop_constants: bool = True) -> pd.DataFrame:
    """
    if drop_constants:
    .dropna() removes undefined entries in correlation matrix after
    it is calculated. Correlations between constants yield nan values since
    they are undefined.
    Passing tuple or list to drop on multiple axes is deprecated since
    version 0.23.0. Therefor split in 2x .dropnan()
    """
    data = get_parameters(ensemble_path)

    # Necessary to drop constant before correlations due to
    # https://github.com/pandas-dev/pandas/issues/37448
    if drop_constants is True:
        for col in data.columns:
            if len(data[col].unique()) == 1:
                data = data.drop(col, axis=1)

    return (
        data.corr()
        if not drop_constants
        else data.corr()
        .dropna(axis="index", how="all")
        .dropna(axis="columns", how="all")
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_parameters(ensemble_path: Path) -> pd.DataFrame:
    return (
        scratch_ensemble("", ensemble_path)
        .parameters.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all", axis="columns")
    )
