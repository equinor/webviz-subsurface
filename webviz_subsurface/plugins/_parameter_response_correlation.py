from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
from webviz_config.utils import calculate_slider_step

from .._datainput.fmu_input import load_parameters, load_csv


class ParameterResponseCorrelation(WebvizPluginABC):
    """### Parameter and response correlation

This plugin shows correlation between numerical input parameters and responses.

Input can be given either as:

  - Aggregated csv files for parameters and responses,
  - An ensemble name defined in shared_settings and a local csv file for responses
stored per realizations.

**Note**: Non-numerical (string-based) input parameters and responses are removed.

**Note**: The response csv file will be aggregated per realization.

Arguments:

* `parameter_csv`: Aggregated csvfile for input parameters with 'REAL' and 'ENSEMBLE' columns.
* `response_csv`: Aggregated csvfile for response parameters with 'REAL' and 'ENSEMBLE' columns.
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `response_file`: Local (per realization) csv file for response parameters.
* `response_filters`: Optional dictionary of responses (columns in csv file) that can be used
as row filtering before aggregation. (See below for filter types).

* `response_ignore`: Response (columns in csv) to ignore (cannot use with response_include).
* `response_include`: Response (columns in csv) to include (cannot use with response_ignore).
* `aggreation`: How to aggregate responses per realization. Either `sum` or `mean`.
* `corr_method`: Correlation algorithm. Either `pearson` or `spearman`.

The types of response_filters are:
```
- `single`: Dropdown with single selection.
- `multi`: Dropdown with multiple selection.
- `range`: Slider with range selection.
```
"""

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        app,
        parameter_csv: Path = None,
        response_csv: Path = None,
        ensembles: list = None,
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        aggregation: str = "sum",
        corr_method: str = "pearson",
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.response_ignore = response_ignore if response_ignore else None
        self.corr_method = corr_method
        self.aggregation = aggregation
        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "csv files" or '
                    '"ensembles and response_file".'
                )
            self.parameterdf = read_csv(self.parameter_csv)
            self.responsedf = read_csv(self.response_csv)

        elif ensembles and response_file:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
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

        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        steps = [
            {
                "id": self.ids("layout"),
                "content": (
                    "Dashboard displaying correlation between selected "
                    "response and input parameters."
                ),
            },
            {
                "id": self.ids("correlation-graph"),
                "content": (
                    "Visualization of the correlations between currently selected "
                    "response and input parameters ranked by the absolute correlation "
                    "coefficient. Click on any correlation to visualize the distribution "
                    "between that parameter and the response."
                ),
            },
            {
                "id": self.ids("distribution-graph"),
                "content": (
                    "Visualized the distribution of the response and the selected input parameter "
                    "in the correlation chart."
                ),
            },
            {"id": self.ids("ensemble"), "content": ("Select the active ensemble."),},
            {"id": self.ids("responses"), "content": ("Select the active response."),},
        ]
        if self.response_filters:
            steps.append(
                {
                    "id": self.ids("filter-wrapper"),
                    "content": (
                        "Filter the response data before calculating correlations."
                    ),
                },
            )
        return steps

    @property
    def responses(self):
        """Returns valid responses. Filters out non numerical columns,
        and filterable columns"""
        responses = list(
            self.responsedf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return [p for p in responses if p not in self.response_filters.keys()]

    @property
    def parameters(self):
        """Returns numerical input parameters"""
        parameters = list(
            self.parameterdf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return parameters

    @property
    def ensembles(self):
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    def check_runs(self):
        """Check that input parameters and response files have
        the same number of runs"""
        for col in ["ENSEMBLE", "REAL"]:
            if sorted(list(self.parameterdf[col].unique())) != sorted(
                list(self.responsedf[col].unique())
            ):
                raise ValueError("Parameter and response files have different runs")

    def check_response_filters(self):
        """'Check that provided response filters are valid"""
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
        """Layout to display selectors for response filters"""
        if not self.response_filters:
            return html.Div(id=self.ids("filter-wrapper"))
        children = [html.Label("Filters")]
        for col_name, col_type in self.response_filters.items():
            domid = self.ids(f"filter-{col_name}")
            if col_type in ("multi", "single"):
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
                children.append(make_range_slider(domid, values, col_name))
        return html.Div(
            id=self.ids("filter-wrapper"), style={"zIndex": 1000}, children=children
        )

    @property
    def control_layout(self):
        """Layout to select e.g. iteration and response"""
        return html.Div(
            style=self.set_grid_layout("1fr 1fr 1fr 1fr"),
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        dcc.Dropdown(
                            id=self.ids("ensemble"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            clearable=False,
                            value=self.ensembles[0],
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label("Response"),
                        dcc.Dropdown(
                            id=self.ids("responses"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.responses
                            ],
                            clearable=False,
                            value=self.responses[0],
                        ),
                    ]
                ),
            ],
        )

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            id=self.ids("layout"),
            children=[
                self.control_layout,
                html.Div(
                    style=self.set_grid_layout("2fr 2fr 1fr")
                    if self.response_filters
                    else self.set_grid_layout("2fr 2fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Div(
                                    children=wcc.Graph(self.ids("correlation-graph")),
                                ),
                            ],
                        ),
                        html.Div(children=[wcc.Graph(self.ids("distribution-graph"))],),
                        self.filter_layout if self.response_filters else html.Div(),
                    ],
                ),
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
        """List of Inputs for correlation callback"""
        callbacks = [
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(Input(self.ids(f"filter-{col_name}"), "value"))
        return callbacks

    @property
    def distribution_input_callbacks(self):
        """List of Inputs for distribution callback"""
        callbacks = [
            Input(self.ids("correlation-graph"), "clickData"),
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(Input(self.ids(f"filter-{col_name}"), "value"))
        return callbacks

    def make_response_filters(self, filters):
        """Returns a list of active response filters"""
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
            """Callback to update correlation graph

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Correlate merged dataframe
            5. Sort correlation for selected response by absolute values
            6. Remove nan values return correlation graph
            """

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
            corrdf = correlate(df, method=self.corr_method)
            corrdf = corrdf.reindex(corrdf[response].abs().sort_values().index)
            try:
                corr_response = (
                    corrdf[response].dropna().drop(["REAL", response], axis=0)
                )
                return make_correlation_plot(
                    corr_response, response, self.plotly_theme, self.corr_method
                )
            except KeyError:
                return {
                    "layout": {
                        "title": "<b>Cannot calculate correlation for given selection</b><br>"
                        "Select a different response or filter setting."
                    }
                }

        @app.callback(
            Output(self.ids("distribution-graph"), "figure"),
            self.distribution_input_callbacks,
        )
        def _update_distribution_graph(clickdata, ensemble, response, *filters):
            """Callback to update distribution graphs.

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Generate scatterplot and histograms
            """
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
            return make_distribution_plot(df, parameter, response, self.plotly_theme)

    def add_webvizstore(self):
        if self.parameter_csv and self.response_csv:
            return [
                (read_csv, [{"csv_file": self.parameter_csv,}],),
                (read_csv, [{"csv_file": self.response_csv,}],),
            ]
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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_and_sum_responses(
    dframe, ensemble, response, filteroptions=None, aggregation="sum"
):
    """Cached wrapper for _filter_and_sum_responses"""
    return _filter_and_sum_responses(
        dframe=dframe,
        ensemble=ensemble,
        response=response,
        filteroptions=filteroptions,
        aggregation=aggregation,
    )


def _filter_and_sum_responses(
    dframe, ensemble, response, filteroptions=None, aggregation="sum",
):
    """Filter response dataframe for the given ensemble
    and optional filter columns. Returns dataframe grouped and
    aggregated per realization."""

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
    if aggregation == "mean":
        return df.groupby("REAL").mean().reset_index()[["REAL", response]]
    raise ValueError(
        f"Aggregation of response file specified as '{aggregation}'' is invalid. "
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def correlate(inputdf, method="pearson"):
    """Cached wrapper for _correlate"""
    return _correlate(inputdf=inputdf, method=method)


def _correlate(inputdf, method="pearson"):
    """Returns the correlation matrix for a dataframe"""
    if method == "pearson":
        return inputdf.corr(method=method)
    if method == "spearman":
        return inputdf.rank().corr(method="pearson")
    raise ValueError(
        f"Correlation method {method} is invalid. "
        "Available methods are 'pearson' and 'spearman'"
    )


def make_correlation_plot(series, response, theme, corr_method):
    """Make Plotly trace for correlation plot"""
    layout = theme_layout(
        theme,
        {
            "barmode": "relative",
            "margin": {"l": 200, "r": 50, "b": 20, "t": 100},
            "height": 750,
            "xaxis": {"range": [-1, 1]},
            "title": f"Correlations ({corr_method}) between {response} and input parameters",
        },
    )
    layout["font"].update({"size": 8})

    return {
        "data": [
            {"x": series.values, "y": series.index, "orientation": "h", "type": "bar"}
        ],
        "layout": layout,
    }


def make_distribution_plot(df, parameter, response, theme):
    """Make plotly traces for scatterplot and histograms for selected
    response and input parameter"""

    real_text = [f"Realization:{r}" for r in df["REAL"]]
    fig = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{"colspan": 2, "rowspan": 2}, None],
            [None, None],
            [{"rowspan": 2}, {"rowspan": 2}],
            [None, None],
        ],
    )
    fig.add_trace(
        {
            "type": "scatter",
            "showlegend": False,
            "mode": "markers",
            "x": df[parameter],
            "y": df[response],
            "text": real_text,
        },
        1,
        1,
    )
    fig.add_trace(
        {"type": "histogram", "x": df[parameter], "showlegend": False,}, 3, 1,
    )
    fig.add_trace(
        {"type": "histogram", "x": df[response], "showlegend": False,}, 3, 2,
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "height": 800,
                "bargap": 0.05,
                "xaxis": {"title": parameter,},
                "yaxis": {"title": response},
                "xaxis2": {"title": parameter},
                "xaxis3": {"title": response},
                "title": f"Distribution of {response} and {parameter}",
            },
        )
    )
    fig["layout"]["font"].update({"size": 8})
    return fig


def make_range_slider(domid, values, col_name):
    try:
        values.apply(pd.to_numeric, errors="raise")
    except ValueError:
        raise ValueError(
            f"Cannot calculate filter range for {col_name}. "
            "Ensure that it is a numerical column."
        )
    return dcc.RangeSlider(
        id=domid,
        min=values.min(),
        max=values.max(),
        step=calculate_slider_step(
            min_value=values.min(),
            max_value=values.max(),
            steps=len(list(values.unique())) - 1,
        ),
        value=[values.min(), values.max()],
        marks={
            str(values.min()): {"label": f"{values.min():.2f}"},
            str(values.max()): {"label": f"{values.max():.2f}"},
        },
    )


def theme_layout(theme, specific_layout):
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)
