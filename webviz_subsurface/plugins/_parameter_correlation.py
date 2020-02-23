from uuid import uuid4

import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.fmu_input import scratch_ensemble


class Widgets:
    @staticmethod
    def dropdown_from_dict(dom_id, dictionary):
        return dcc.Dropdown(
            id=dom_id,
            options=[{"label": k, "value": v} for k, v in dictionary.items()],
            value=list(dictionary.values())[0],
            clearable=False,
        )


class ParameterCorrelation(WebvizPluginABC):
    """### Parameter correlation

Shows parameter correlation using a correlation matrix,
and scatter plot for any given pair of parameters.

* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `drop_constants`: Drop constant parameters
"""

    def __init__(self, app, ensembles, drop_constants: bool = True):

        super().__init__()

        self.ensembles = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.drop_constants = drop_constants
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme

        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def p_cols(self):
        dfs = [
            get_corr_data(ens, self.drop_constants) for ens in self.ensembles.values()
        ]
        return sorted(list(pd.concat(dfs).columns))

    @property
    def matrix_plot(self):
        return html.Div(
            style={"height": "400px"},
            children=wcc.Graph(
                id=self.ids("matrix"),
                clickData={"points": [{"x": self.p_cols[0], "y": self.p_cols[0]}]},
            ),
        )

    @property
    def control_div(self):
        return html.Div(
            style={"padding-top": 10},
            children=[
                html.Div(
                    children=[
                        html.Label(
                            "Set ensemble in all plots:", style={"font-weight": "bold"}
                        ),
                        html.Div(
                            style={
                                "padding-bottom": 20,
                                "display": "grid",
                                "grid-template-columns": "1fr 4fr",
                            },
                            children=[
                                Widgets.dropdown_from_dict(
                                    self.ids("ensemble-all"), self.ensembles
                                )
                            ],
                        ),
                        html.Label(
                            "Parameter horisontal axis:", style={"font-weight": "bold"}
                        ),
                        html.Div(
                            style={
                                "padding-bottom": 20,
                                "display": "grid",
                                "grid-template-columns": "4fr 1fr",
                            },
                            children=[
                                dcc.Dropdown(
                                    id=self.ids("parameter1"),
                                    options=[
                                        {"label": p, "value": p} for p in self.p_cols
                                    ],
                                    value=self.p_cols[0],
                                    clearable=False,
                                ),
                                Widgets.dropdown_from_dict(
                                    self.ids("ensemble-1"), self.ensembles
                                ),
                            ],
                        ),
                        html.Label(
                            "Parameter vertical axis:", style={"font-weight": "bold"}
                        ),
                        html.Div(
                            style={
                                "padding-bottom": 20,
                                "display": "grid",
                                "grid-template-columns": "4fr 1fr",
                            },
                            children=[
                                dcc.Dropdown(
                                    id=self.ids("parameter2"),
                                    options=[
                                        {"label": p, "value": p} for p in self.p_cols
                                    ],
                                    value=self.p_cols[0],
                                    clearable=False,
                                ),
                                Widgets.dropdown_from_dict(
                                    self.ids("ensemble-2"), self.ensembles
                                ),
                            ],
                        ),
                        html.Label("Color scatter by:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.ids("scatter-color"),
                            options=[{"label": p, "value": p} for p in self.p_cols],
                        ),
                    ]
                ),
                html.Div(
                    style={"padding-top": 20,},
                    children=[
                        dcc.Checklist(
                            id=self.ids("density"),
                            options=[
                                {
                                    "label": "Show scatterplot density",
                                    "value": "density",
                                }
                            ],
                        ),
                    ],
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            children=[
                html.Div(
                    style={"display": "grid", "grid-template-columns": "3fr 2fr"},
                    children=[html.Div(children=[self.matrix_plot]), self.control_div],
                ),
                html.Div(
                    style={"display": "grid", "grid-template-columns": "3fr 2fr"},
                    children=wcc.Graph(id=self.ids("scatter")),
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("matrix"), "figure"),
            [
                Input(self.ids("ensemble-all"), "value"),
                Input(self.ids("parameter1"), "value"),
                Input(self.ids("parameter2"), "value"),
            ],
        )
        def _update_matrix(ens, param1, param2):
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
        def _update_scatter(ens1, param1, ens2, param2, color, density):
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
        def _update_from_click(cell_data, ens):
            try:
                points = cell_data["points"][0]
            # TypeError is returned if no cells are clicked
            except TypeError:
                return [None for i in range(4)]

            return [points["x"], points["y"], ens, ens]

    def add_webvizstore(self):
        return [
            ([get_parameters, [{"ensemble_path": v} for v in self.ensembles.values()]])
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_parameters(ensemble_path) -> pd.DataFrame:

    return (
        scratch_ensemble("", ensemble_path)
        .parameters.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all", axis="columns")
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_scatter(ens1, x_col, ens2, y_col, color, density, theme):
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
            "margin": {"t": 20, "b": 50, "l": 200, "r": 200},
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
def get_corr_data(ensemble_path, drop_constants=True):
    """
    if drop_constants:
    .dropna() removes undefined entries in correlation matrix after
    it is calculated. Correlations between constants yield nan values since
    they are undefined.
    Passing tuple or list to drop on multiple axes is deprecated since
    version 0.23.0. Therefor split in 2x .dropnan()
    """
    data = get_parameters(ensemble_path)

    return (
        data.corr()
        if not drop_constants
        else data.corr()
        .dropna(axis="index", how="all")
        .dropna(axis="columns", how="all")
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(ensemble_path, theme, drop_constants=True):
    corrdf = get_corr_data(ensemble_path, drop_constants)
    # pylint: disable=no-member
    corrdf = corrdf.mask(np.tril(np.ones(corrdf.shape)).astype(np.bool))

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
            "xaxis": {"ticks": "", "showticklabels": False, "showgrid": False,},
            "yaxis": {"ticks": "", "showticklabels": False, "showgrid": False,},
        },
    )

    return {"data": [data], "layout": layout}


def theme_layout(theme, specific_layout):
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout
