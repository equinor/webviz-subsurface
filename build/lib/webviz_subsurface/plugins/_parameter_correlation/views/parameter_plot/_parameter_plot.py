from pathlib import Path
from typing import List, Tuple, Type, Union

import numpy as np
import pandas as pd
from dash import Input, Output, State, callback, callback_context, no_update
from dash.development.base_component import Component
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_config.webviz_store import webvizstore
from webviz_core_components import Graph as WccGraph

from webviz_subsurface._datainput.fmu_input import scratch_ensemble

from .settings._parameter_settings import ParameterSettings


class Graph(ViewElementABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        GRAPH = "graph"

    def __init__(self, p_cols: List, height: str = "43vh") -> None:
        super().__init__()
        self.height = height
        self.p_cols = p_cols

    def inner_layout(self) -> Type[Component]:
        return WccGraph(
            id=self.register_component_unique_id(Graph.IDs.GRAPH),
            style={"height": self.height, "min-height": "300px"},
            clickData={
                "points": [
                    {
                        "x": self.p_cols[0] if len(self.p_cols) > 0 else "",
                        "y": self.p_cols[0] if len(self.p_cols) > 0 else "",
                    }
                ]
            },
        )


class ParameterPlot(ViewABC):
    """Class for the two view elements in the Parameter
    Correlation plugin"""

    class IDs:
        # pylint: disable=too-few-public-methods
        MATRIXPLOT = "matrixplot"
        SCATTERPLOT = "scatterplot"
        PARAMETERSETTINGS = "settings"
        MAIN_COLUMN = "main-column"
        MATRIX_ROW = "matrix-row"
        SCATTER_ROW = "scatter-row"

    def __init__(
        self,
        ensembles: dict,
        webviz_settings: WebvizSettings,
        drop_constants: bool = True,
    ) -> None:
        super().__init__("Parameter Correlation")

        self.ensembles = ensembles
        self.drop_constants = drop_constants

        try:
            self.plotly_theme = webviz_settings.theme.plotly_theme
        except AttributeError:
            print("Attribute error: 'Dash' has no attribute 'theme'")
        self.drop_constants = drop_constants

        self.add_settings_group(
            ParameterSettings(self.ensembles, self.p_cols),
            ParameterPlot.IDs.PARAMETERSETTINGS,
        )

        column = self.add_column(ParameterPlot.IDs.MAIN_COLUMN)

        first_row = column.make_row(ParameterPlot.IDs.MATRIX_ROW)
        first_row.add_view_element(Graph(self.p_cols), ParameterPlot.IDs.MATRIXPLOT)

        second_row = column.make_row(ParameterPlot.IDs.SCATTER_ROW)
        second_row.add_view_element(Graph(self.p_cols), ParameterPlot.IDs.SCATTERPLOT)

    @property
    def p_cols(self) -> list:
        dfs = [
            get_corr_data(ens, self.drop_constants) for ens in self.ensembles.values()
        ]
        return sorted(list(pd.concat(dfs, sort=True).columns))

    @property
    def tour_steps(self) -> List[dict]:
        """Tour of the plugin"""
        return [
            {
                "id": self.layout_element(
                    ParameterPlot.IDs.MAIN_COLUMN
                ).get_unique_id(),
                "content": "Displayting correlation between parameteres.",
            },
            {
                "id": self.layout_element(ParameterPlot.IDs.MATRIX_ROW).get_unique_id(),
                "content": "Matrix plot of the parameter correlation. You can "
                "click on the boxes to display the parameters in the scatterplot.",
            },
            {
                "id": self.layout_element(
                    ParameterPlot.IDs.SCATTER_ROW
                ).get_unique_id(),
                "content": "Scatterplot of the parameter correlation.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.SHARED_ENSEMBLE),
                "content": "Choose which ensemble that is desired to show.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.PARAMETER_H),
                "content": "Choose the parameter on the horizontal axis of the "
                "scatterplot.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.ENSEMBLE_H),
                "content": "Choose the ensemble on the horizontal axis of the "
                "scatterplot.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.PARAMETER_V),
                "content": "Choose the parameter on the vertical axis of the "
                "scatterplot.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.ENSEMBLE_V),
                "content": "Choose the ensemble on the vertical axis of the "
                "scatterplot.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.SCATTER_COLOR),
                "content": "Choose optional parameter to color scattered points.",
            },
            {
                "id": self.settings_group(
                    ParameterPlot.IDs.PARAMETERSETTINGS
                ).component_unique_id(ParameterSettings.IDs.SCATTER_VISIBLE),
                "content": "Choose to display density of scattered points.",
            },
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_H)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_V)
                .to_string(),
                "value",
            ),
            Input(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _update_parameter_selections(cell_data: dict) -> Tuple:
            if cell_data is not None:
                return (cell_data["points"][0]["x"], cell_data["points"][0]["y"])
            return no_update

        @callback(
            Output(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.SHARED_ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_H)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_V)
                .to_string(),
                "value",
            ),
            State(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _update_matrix(
            both_ensemble: str,
            horizontal_parameter: str,
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
                x_index = list(fig["data"][0]["x"]).index(horizontal_parameter)
                y_index = list(fig["data"][0]["y"]).index(vertical_parameter)
            else:
                horizontal_parameter = cell_data["points"][0]["x"]
                vertical_parameter = cell_data["points"][0]["y"]
                x_index = list(fig["data"][0]["x"]).index(horizontal_parameter)
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
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_H)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.ENSEMBLE_H)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.PARAMETER_V)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.ENSEMBLE_V)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.SCATTER_COLOR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ParameterPlot.IDs.PARAMETERSETTINGS)
                .component_unique_id(ParameterSettings.IDs.SCATTER_VISIBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _update_scatter(
            horizontal_parameter: str,
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
                    horizontal_parameter,
                    vertical_ensemble,
                    vertical_parameter,
                    color_by,
                    scatter,
                    self.plotly_theme,
                )
            horizontal_parameter = cell_data["points"][0]["x"]
            vertical_parameter = cell_data["points"][0]["y"]
            return render_scatter(
                horizontal_ensemble,
                horizontal_parameter,
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
