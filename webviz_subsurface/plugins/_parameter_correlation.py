from pathlib import Path
from typing import Callable, List, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._datainput.fmu_input import scratch_ensemble


class ParameterCorrelation(WebvizPluginABC):
    """Shows parameter correlations using a correlation matrix,
    and scatter plot for any given pair of parameters.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`drop_constants`:** Drop constant parameters.

    ---
    Parameter values are extracted automatically from the `parameters.txt` files in the individual
    realizations of your defined `ensembles`, using the `fmu-ensemble` library."""

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        drop_constants: bool = True,
    ):

        super().__init__()

        self.ensembles = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.drop_constants = drop_constants
        self.plotly_theme = webviz_settings.theme.plotly_theme

        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def p_cols(self) -> list:
        dfs = [
            get_corr_data(ens, self.drop_constants) for ens in self.ensembles.values()
        ]
        return sorted(list(pd.concat(dfs, sort=True).columns))

    @property
    def matrix_plot(self) -> html.Div:
        return html.Div(
            style={"height": "45vh"},
            children=wcc.Graph(
                id=self.ids("matrix"),
                clickData={"points": [{"x": self.p_cols[0], "y": self.p_cols[0]}]},
            ),
        )

    @property
    def control_div(self) -> list:
        return [
            wcc.Selectors(
                label="Distribution plot horizontal axis",
                children=[
                    wcc.Dropdown(
                        id=self.ids("parameter1"),
                        label="Parameter",
                        options=[{"label": p, "value": p} for p in self.p_cols],
                        value=self.p_cols[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Ensemble",
                        id=self.ids("ensemble-1"),
                        options=[
                            {"label": k, "value": v} for k, v in self.ensembles.items()
                        ],
                        value=list(self.ensembles.values())[0],
                        clearable=False,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Distribution plot vertical axis",
                children=[
                    wcc.Dropdown(
                        id=self.ids("parameter2"),
                        label="Parameter",
                        options=[{"label": p, "value": p} for p in self.p_cols],
                        value=self.p_cols[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Ensemble",
                        id=self.ids("ensemble-2"),
                        options=[
                            {"label": k, "value": v} for k, v in self.ensembles.items()
                        ],
                        value=list(self.ensembles.values())[0],
                        clearable=False,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Distribution plot options",
                children=[
                    wcc.Dropdown(
                        label="Color by",
                        id=self.ids("scatter-color"),
                        options=[{"label": p, "value": p} for p in self.p_cols],
                    ),
                    wcc.Checklist(
                        id=self.ids("density"),
                        style={"padding": "5px"},
                        options=[
                            {
                                "label": "Show scatterplot density",
                                "value": "density",
                            }
                        ],
                    ),
                ],
            ),
        ]

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.Selectors(
                            label="Ensemble in both plots",
                            children=wcc.Dropdown(
                                id=self.ids("ensemble-all"),
                                options=[
                                    {"label": k, "value": v}
                                    for k, v in self.ensembles.items()
                                ],
                                value=list(self.ensembles.values())[0],
                                clearable=False,
                            ),
                        )
                    ]
                    + self.control_div,
                ),
                wcc.Frame(
                    style={"flex": 6, "height": "90vh"},
                    children=[
                        html.Div(
                            children=[
                                self.matrix_plot,
                                wcc.Graph(
                                    style={"height": "45vh"}, id=self.ids("scatter")
                                ),
                            ],
                        )
                    ],
                ),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.ids("matrix"), "figure"),
            [
                Input(self.ids("ensemble-all"), "value"),
                Input(self.ids("parameter1"), "value"),
                Input(self.ids("parameter2"), "value"),
            ],
        )
        def _update_matrix(ens: str, param1: str, param2: str) -> dict:
            """Renders correlation matrix.
            Currently also re-renders matrix to update currently
            selected cell. This is not optimal, but hard to prevent
            as an Output object only can have one callback attached,
            and it is not possible to assign callbacks to individual
            elements of a Plotly graph object
            """
            fig = render_matrix(
                ens, theme=self.plotly_theme, drop_constants=self.drop_constants
            )
            # Finds index of the currently selected cell
            x_index = list(fig["data"][0]["x"]).index(param1)
            y_index = list(fig["data"][0]["y"]).index(param2)
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

        @app.callback(
            Output(self.ids("scatter"), "figure"),
            [
                Input(self.ids("ensemble-1"), "value"),
                Input(self.ids("parameter1"), "value"),
                Input(self.ids("ensemble-2"), "value"),
                Input(self.ids("parameter2"), "value"),
                Input(self.ids("scatter-color"), "value"),
                Input(self.ids("density"), "value"),
            ],
        )
        def _update_scatter(
            ens1: str,
            param1: str,
            ens2: str,
            param2: str,
            color: Union[str, None],
            density: List[str],
        ) -> dict:
            return render_scatter(
                ens1, param1, ens2, param2, color, density, self.plotly_theme
            )

        @app.callback(
            [
                Output(self.ids("parameter1"), "value"),
                Output(self.ids("parameter2"), "value"),
                Output(self.ids("ensemble-1"), "value"),
                Output(self.ids("ensemble-2"), "value"),
            ],
            [
                Input(self.ids("matrix"), "clickData"),
                Input(self.ids("ensemble-all"), "value"),
            ],
        )
        def _update_from_click(cell_data: dict, ens: str) -> List[Union[str, None]]:
            try:
                points = cell_data["points"][0]
            # TypeError is returned if no cells are clicked
            except TypeError:
                return [None for i in range(4)]

            return [points["x"], points["y"], ens, ens]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (get_parameters, [{"ensemble_path": v} for v in self.ensembles.values()])
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_parameters(ensemble_path: Path) -> pd.DataFrame:

    return (
        scratch_ensemble("", ensemble_path)
        .parameters.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all", axis="columns")
    )


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


def theme_layout(theme: dict, specific_layout: dict) -> dict:
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout
