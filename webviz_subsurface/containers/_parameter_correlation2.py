from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizContainerABC

from .._datainput.fmu_input import load_parameters, load_csv


class ParameterCorrelation2(WebvizContainerABC):
    """### Parameter Correlation

This container shows parameter correlation using a correlation matrix,
and scatter plot for any given pair of parameters.

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `drop_constants`: Drop constant parameters
"""

    def __init__(
        self,
        app,
        container_settings,
        parameter_csv: Path = None,
        response_csv: Path = None,
        ensembles: list = None,
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        aggregation: str = "sum",
        method: str = "pearson",
    ):

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.response_ignore = response_ignore if response_ignore else None
        self.method = method
        self.aggregation = aggregation
        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. either provide "response_include", "response_ignore" or neither'
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "csv files" or "ensembles and response_file".'
                )
            self.parameterdf = read_csv(self.parameter_csv)
            self.responsedf = read_csv(self.response_csv)

        elif ensembles and response_file:
            self.ens_paths = tuple(
                (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
            )
            self.parameterdf = load_parameters(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
            self.responsedf = load_csv(
                ensemble_paths=self.ens_paths,
                csv_file=response_file,
                ensemble_set_name="EnsembleSet",
            )
        else:
            raise ValueError(
                'Incorrect arguments. Either provide "csv files" or "ensembles and response_file".'
            )
        self.check_runs()
        self.check_response_filters()
        if response_ignore:
            self.responsedf.drop(response_ignore, errors="ignore", axis=1, inplace=True)
        if response_include:
            self.responsedf.drop(
                self.responsedf.columns.difference(
                    [
                        "REAL",
                        "ENSEMBLE",
                        *response_include,
                        *list(response_filters.keys()),
                    ]
                ),
                errors="ignore",
                axis=1,
                inplace=True,
            )

        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def responses(self):
        responses = list(
            self.responsedf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return [p for p in responses if p not in self.response_filters.keys()]

    @property
    def parameters(self):
        parameters = list(
            self.parameterdf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return parameters

    @property
    def ensembles(self):
        return list(self.parameterdf["ENSEMBLE"].unique())

    def check_runs(self):
        for col in ["ENSEMBLE", "REAL"]:
            if sorted(list(self.parameterdf[col].unique())) != sorted(
                list(self.responsedf[col].unique())
            ):
                raise ValueError("Parameter and response files have different runs")

    def check_response_filters(self):
        if self.response_filters:
            for col_name, col_type in self.response_filters.items():
                if col_name not in self.responsedf.columns:
                    raise ValueError(f"{col_name} is not in response file")
                if col_type not in ["single", "multi", "range"]:
                    raise ValueError(
                        f"Filter type {col_type} for {col_name} is not valid."
                    )

    @property
    def filter_layout(self):
        if not self.response_filters:
            return
        children = [html.Label("Filters")]
        for col_name, col_type in self.response_filters.items():
            domid = self.ids(f"filter-{col_name}")
            if col_type == "multi" or col_type == "single":
                values = list(self.responsedf[col_name].unique())
                children.append(html.Label(col_name))
                children.append(
                    dcc.Dropdown(
                        id=domid,
                        options=[{"label": val, "value": val} for val in values],
                        value=values if col_type == "multi" else values[0],
                        multi=col_type == "multi",
                        clearable=False,
                    )
                )
            elif col_type == "range":
                values = self.responsedf[col_name]
                children.append(html.Label(col_name))
                children.append(make_range_slider(domid, values)),
        return html.Div(children=children)

    @property
    def control_layout(self):
        return html.Div(
            children=[
                dcc.Dropdown(
                    id=self.ids("ensemble"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    clearable=False,
                    value=self.ensembles[0],
                ),
                dcc.Dropdown(
                    id=self.ids("responses"),
                    options=[{"label": ens, "value": ens} for ens in self.responses],
                    clearable=False,
                    value=self.responses[0],
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("2fr 2fr 1fr")
            if self.response_filters
            else self.set_grid_layout("2fr 2fr"),
            children=[
                html.Div(
                    style={"height": "100%", "width": "100%"},
                    children=[
                        self.control_layout,
                        html.Div(children=wcc.Graph(self.ids("correlation-graph")),),
                    ],
                ),
                html.Div(
                    style={"height": "100%", "width": "100%"},
                    children=[wcc.Graph(self.ids("distribution-graph"))],
                ),
                self.filter_layout if self.response_filters else html.Div(),
            ],
        )

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def correlation_input_callbacks(self):
        callbacks = [
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters.keys():
                callbacks.append(Input(self.ids(f"filter-{col_name}"), "value"))
        return callbacks

    @property
    def distribution_input_callbacks(self):
        callbacks = [
            Input(self.ids("correlation-graph"), "clickData"),
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters.keys():
                callbacks.append(Input(self.ids(f"filter-{col_name}"), "value"))
        return callbacks

    def make_response_filters(self, filters):
        filteroptions = []
        if filters:
            for i, (col_name, col_type) in enumerate(self.response_filters.items()):
                filteroptions.append(
                    {"name": col_name, "type": col_type, "values": filters[i]}
                )
        return filteroptions

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("correlation-graph"), "figure"),
            self.correlation_input_callbacks,
        )
        def _update_correlation_graph(ensemble, response, *filters):

            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])
            corrdf = correlate(df)
            corrdf = corrdf.reindex(corrdf[response].abs().sort_values().index)
            try:
                corr_response = (
                    corrdf[response].dropna().drop(["REAL", response], axis=0)
                )
                return correlation_plot(corr_response)
            except KeyError:
                return {"data": []}

        @app.callback(
            Output(self.ids("distribution-graph"), "figure"),
            self.distribution_input_callbacks,
        )
        def _update_distribution_graph(clickdata, ensemble, response, *filters):
            if not clickdata:
                raise PreventUpdate
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            parameter = clickdata["points"][0]["y"]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])[
                ["REAL", parameter, response]
            ]
            return render_scatter(df, parameter, response)
            # raise preventupdate

    def add_webvizstore(self):
        if self.parameter_csv and self.response_csv:
            return [
                (read_csv, [{"csv_file": self.parameter_csv,}],)(
                    read_csv, [{"csv_file": self.parameter_csv,}],
                )
            ]
        else:
            return [
                (
                    load_parameters,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                        }
                    ],
                ),
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": self.response_file,
                            "ensemble_set_name": "EnsembleSet",
                        }
                    ],
                ),
            ]


def filter_and_sum_responses(
    dframe, ensemble, response, filteroptions=None, aggregation="sum",
):
    df = dframe.copy()
    df = df.loc[df["ENSEMBLE"] == ensemble]
    if filteroptions:
        for opt in filteroptions:
            if opt["type"] == "multi" or opt["type"] == "single":
                if isinstance(opt["values"], list):
                    df = df.loc[df[opt["name"]].isin(opt["values"])]
                else:
                    df = df.loc[df[opt["name"]] == opt["values"]]

            elif opt["type"] == "range":
                df = df.loc[
                    (df[opt["name"]] >= np.min(opt["values"]))
                    & (df[opt["name"]] <= np.max(opt["values"]))
                ]
    if aggregation == "sum":
        return df.groupby("REAL").sum().reset_index()[["REAL", response]]
    elif aggregation == "mean":
        return df.groupby("REAL").mean().reset_index()[["REAL", response]]
    else:
        raise ValueError(
            f"Aggregation of response file specified as {aggregation} is invalid. "
        )


def correlate(inputdf, method="spearman"):

    return inputdf.corr(method=method)


def correlation_plot(series):

    return {
        "data": [
            {"x": series.values, "y": series.index, "orientation": "h", "type": "bar"}
        ],
        "layout": {
            "barmode": "relative",
            "margin": {"l": 200, "r": 50, "b": 20, "t": 50},
            "font": {"size": 10},
            "height": 800,
            "xaxis": {"range": [-1, 1]},
        },
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_scatter(df, parameter, response):

    # real_text = [f"Realization:{r}" for r in df["REAL"]]

    # Make a plotly subplot figure
    fig = make_subplots(
        rows=4,
        cols=2,
        vertical_spacing=0.05,
        specs=[
            [{"colspan": 2, "rowspan": 2}, None],
            [None, None],
            [{"rowspan": 2}, {"rowspan": 2}],
            [None, None],
        ],
    )

    # color = df[color] if color else None
    data = []
    fig.add_trace(
        {
            "type": "scatter",
            "showlegend": False,
            "mode": "markers",
            "x": df[parameter],
            "y": df[response],
        },
        1,
        1,
    )
    fig.add_trace(
        {
            "type": "histogram",
            "marker": {"color": "rgb(31, 119, 180)"},
            "x": df[parameter],
            "showlegend": False,
        },
        3,
        1,
    )
    fig.add_trace(
        {
            "type": "histogram",
            "marker": {"color": "rgb(31, 119, 180)"},
            "x": df[response],
            "showlegend": False,
        },
        3,
        2,
    )

    fig["layout"].update(
        {
            "height": 800,
            "bargap": 0.05,
            "xaxis": {"title": parameter,},
            "yaxis": {"title": response},
            "xaxis2": {"title": parameter},
            "xaxis3": {"title": response},
        }
    )
    return fig


def make_range_slider(domid, values):
    try:
        values.apply(pd.to_numeric, errors="raise")
    except ValueError:
        raise ValueError(
            f"Cannot calculate filter range for {col_name}. Ensure that it is a numerical column."
        )
    return dcc.RangeSlider(
        id=domid,
        min=values.min(),
        max=values.max(),
        step=(values.max() - values.min()) / len(list(values.unique())) - 1,
        value=[values.min(), values.max()],
        marks={
            str(values.min()): {"label": f"{values.min():.2f}"},
            str(values.max()): {"label": f"{values.max():.2f}"},
        },
    )
