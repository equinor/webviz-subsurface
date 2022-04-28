from pathlib import Path

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore

import webviz_subsurface._utils.parameter_response as parresp
from webviz_subsurface._datainput.fmu_input import load_csv, load_parameters
from webviz_subsurface._figures import create_figure
from webviz_subsurface._models import (
    EnsembleSetModel,
    ParametersModel,
    caching_ensemble_set_model_factory,
)


class ParameterResponseCorrelation(WebvizPluginABC):
    """Visualizes correlations between numerical input parameters and responses.

---
**Three main options for input data: Aggregated, file per realization and read from UNSMRY.**

**Using aggregated data**
* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns \
(absolute path or relative to config file).
* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` \
columns (absolute path or relative to config file).


**Using a response file per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be \
                    combined with `response_csv` and `parameter_csv`).


**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` \
                implies that the input data should be time series data from simulation `.UNSMRY` \
                files, read using `fmu-ensemble`.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading \
                from UNSMRY-files in the defined ensembles (default is all vectors). * can be \
                used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from \
               `.UNSMRY`-files (default is monthly).

?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter \
   of type `single` (as defined below under `response_filters`).


**Common settings for all input options**

All of these are optional, some have defaults seen in the code snippet below.

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation \
                       vectors) that can be used as row filtering before aggregation. \
                       Valid options:
    * `single`: Dropdown with single selection.
    * `multi`: Dropdown with multiple selection.
    * `range`: Slider with range selection.
* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore \
                      (cannot use with response_include).
* **`response_include`:** List of response (columns in csv or simulation vectors) to include \
                       (cannot use with response_ignore).
* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.
* **`corr_method`:** Correlation method. Either `pearson` or `spearman`.

---

?> Non-numerical (string-based) input parameters and responses are removed.

?> The responses will be aggregated per realization; meaning that if your filters do not reduce \
the response to a single value per realization in your data, the values will be aggregated \
accoording to your defined `aggregation`. If e.g. the response is a form of volume, \
and the filters are regions (or other subdivisions of the total volume), then `sum` would \
be a natural aggregation. If on the other hand the response is the pressures in the \
same volume, aggregation as `mean` over the subdivisions of the same volume \
would make more sense (though the pressures in this case would not be volume weighted means, \
and the aggregation would therefore likely be imprecise).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like \
`monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics are calculated per DATE over \
all realizations in an ensemble, and the available dates should therefore not differ between \
individual realizations of an ensemble.

**Using aggregated data**

The `parameter_csv` file must have columns `REAL`, `ENSEMBLE` and the parameter columns.

The `response_csv` file must have columns `REAL`, `ENSEMBLE` and the response columns \
(and the columns to use as `response_filters`, if that option is used).


**Using a response file per realization**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

The `response_file` must have the response columns (and the columns to use as `response_filters`, \
if that option is used).


**Using simulation time series data directly from `UNSMRY` files as responses**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

Responses are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.
"""

    # pylint:disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        parameter_csv: Path = None,
        response_csv: Path = None,
        ensembles: list = None,
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
        corr_method: str = "pearson",
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.column_keys = column_keys
        self.time_index = sampling
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
            parameterdf = read_csv(self.parameter_csv)
            self.responsedf = read_csv(self.response_csv)

        elif ensembles:
            self.ens_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            parameterdf = load_parameters(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
            if self.response_file:
                self.responsedf = load_csv(
                    ensemble_paths=self.ens_paths,
                    csv_file=response_file,
                    ensemble_set_name="EnsembleSet",
                )
            else:
                self.emodel: EnsembleSetModel = (
                    caching_ensemble_set_model_factory.get_or_create_model(
                        ensemble_paths=self.ens_paths,
                        column_keys=self.column_keys,
                        time_index=self.time_index,
                    )
                )
                self.responsedf = self.emodel.get_or_load_smry_cached()
                self.response_filters["DATE"] = "single"
        else:
            raise ValueError(
                'Incorrect arguments. Either provide "csv files" or "ensembles and response_file".'
            )
        pmodel = ParametersModel(
            dataframe=parameterdf, keep_numeric_only=True, drop_constants=True
        )
        self.parameterdf = pmodel.dataframe
        self.parameter_columns = pmodel.parameters
        parresp.check_runs(self.parameterdf, self.responsedf)
        parresp.check_response_filters(self.responsedf, self.response_filters)

        # Only select numerical responses
        self.response_columns = parresp.filter_numerical_columns(
            df=self.responsedf,
            column_ignore=response_ignore,
            column_include=response_include,
            filter_columns=self.response_filters.keys(),
        )

        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    @property
    def tour_steps(self):
        steps = [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard displaying correlation between selected "
                    "response and input parameters."
                ),
            },
            {
                "id": self.uuid("correlation-graph"),
                "content": (
                    "Visualization of the correlations between currently selected "
                    "response and input parameters ranked by the absolute correlation "
                    "coefficient. Click on any correlation to visualize the distribution "
                    "between that parameter and the response."
                ),
            },
            {
                "id": self.uuid("distribution-graph"),
                "content": (
                    "Visualized the distribution of the response and the selected input parameter "
                    "in the correlation chart."
                ),
            },
            {
                "id": self.uuid("ensemble"),
                "content": ("Select the active ensemble."),
            },
            {
                "id": self.uuid("responses"),
                "content": ("Select the active response."),
            },
        ]

        return steps

    @property
    def ensembles(self):
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def filter_layout(self):
        """Layout to display selectors for response filters"""
        children = []
        for col_name, col_type in self.response_filters.items():
            domid = self.uuid(f"filter-{col_name}")
            values = list(self.responsedf[col_name].unique())
            if col_type == "multi":
                selector = wcc.SelectWithLabel(
                    label=col_name,
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                    size=min(20, len(values)),
                )
            elif col_type == "single":
                selector = wcc.Dropdown(
                    label=col_name,
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    multi=False,
                    clearable=False,
                )
            elif col_type == "range":
                selector = make_range_slider(domid, self.responsedf[col_name], col_name)
            else:
                return children
            children.append(selector)

        return children

    @property
    def control_layout(self):
        """Layout to select e.g. iteration and response"""
        max_params = len(self.parameter_columns)
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.uuid("ensemble"),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                clearable=False,
                value=self.ensembles[0],
            ),
            wcc.Dropdown(
                label="Response",
                id=self.uuid("responses"),
                options=[{"label": ens, "value": ens} for ens in self.response_columns],
                clearable=False,
                value=self.response_columns[0],
            ),
            html.Div(
                wcc.Slider(
                    label="Max number of parameters",
                    id=self.uuid("max-params"),
                    min=1,
                    max=max_params,
                    step=1,
                    marks={1: "1", max_params: str(max_params)},
                    value=max_params,
                ),
                style={"marginTop": "10px"},
            ),
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.FlexColumn(
                    flex=1,
                    children=wcc.Frame(
                        style={"height": "80vh"},
                        children=[
                            wcc.Selectors(
                                label="Controls", children=self.control_layout
                            )
                        ]
                        + (
                            [
                                wcc.Selectors(
                                    label="Filters", children=self.filter_layout
                                )
                            ]
                            if self.response_filters
                            else []
                        ),
                    ),
                ),
                wcc.FlexColumn(
                    flex=3,
                    children=wcc.Frame(
                        color="white",
                        highlight=False,
                        style={"height": "80vh"},
                        children=[
                            wcc.Graph(
                                style={"height": "75vh"},
                                id=self.uuid("correlation-graph"),
                            ),
                            dcc.Store(
                                id=self.uuid("initial-parameter"),
                                storage_type="session",
                            ),
                        ],
                    ),
                ),
                wcc.FlexColumn(
                    flex=3,
                    children=wcc.Frame(
                        color="white",
                        highlight=False,
                        style={"height": "80vh"},
                        children=wcc.Graph(
                            style={"height": "75vh"}, id=self.uuid("distribution-graph")
                        ),
                    ),
                ),
            ],
        )

    @property
    def correlation_input_callbacks(self):
        """List of Inputs for correlation callback"""
        callbacks = [
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("responses"), "value"),
            Input(self.uuid("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(Input(self.uuid(f"filter-{col_name}"), "value"))
        return callbacks

    @property
    def distribution_input_callbacks(self):
        """List of Inputs for distribution callback"""
        callbacks = [
            Input(self.uuid("correlation-graph"), "clickData"),
            Input(self.uuid("initial-parameter"), "data"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(Input(self.uuid(f"filter-{col_name}"), "value"))
        return callbacks

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("correlation-graph"), "figure"),
                Output(self.uuid("initial-parameter"), "data"),
            ],
            self.correlation_input_callbacks,
        )
        def _update_correlation_graph(ensemble, response, max_parameters, *filters):
            """Callback to update correlation graph

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Correlate merged dataframe
            5. Sort correlation for selected response by absolute values
            6. Remove nan values return correlation graph
            """

            filteroptions = parresp.make_response_filters(
                response_filters=self.response_filters,
                response_filter_values=filters,
            )
            responsedf = parresp.filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])
            corrdf = correlate(df, response=response, method=self.corr_method)
            try:
                corr_response = (
                    corrdf[response]
                    .dropna()
                    .drop(["REAL", response], axis=0)
                    .tail(n=max_parameters)
                )

                return (
                    make_correlation_plot(
                        corr_response, response, self.theme, self.corr_method
                    ),
                    corr_response.index[-1],
                )
            except KeyError:
                return (
                    {
                        "layout": {
                            "title": "<b>Cannot calculate correlation for given selection</b><br>"
                            "Select a different response or filter setting."
                        }
                    },
                    None,
                )

        @app.callback(
            Output(self.uuid("distribution-graph"), "figure"),
            self.distribution_input_callbacks,
        )
        def _update_distribution_graph(
            clickdata, initial_parameter, ensemble, response, *filters
        ):
            """Callback to update distribution graphs.

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Generate scatterplot and histograms
            """
            if clickdata:
                parameter = clickdata["points"][0]["y"]
            elif initial_parameter:
                parameter = initial_parameter
            else:
                return {}
            filteroptions = parresp.make_response_filters(
                response_filters=self.response_filters,
                response_filter_values=filters,
            )
            responsedf = parresp.filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])[
                ["REAL", parameter, response]
            ]
            return make_distribution_plot(df, parameter, response, self.theme)

    def add_webvizstore(self):
        if self.parameter_csv and self.response_csv:
            return [
                (
                    read_csv,
                    [
                        {
                            "csv_file": self.parameter_csv,
                        }
                    ],
                ),
                (
                    read_csv,
                    [
                        {
                            "csv_file": self.response_csv,
                        }
                    ],
                ),
            ]

        functions = [
            (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            ),
        ]
        if self.response_file:
            functions.append(
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": self.response_file,
                            "ensemble_set_name": "EnsembleSet",
                        }
                    ],
                )
            )
        else:
            functions.extend(self.emodel.webvizstore)
        return functions


def correlate(inputdf, response, method="pearson"):
    """Returns the correlation matrix for a dataframe"""
    if method == "pearson":
        corrdf = inputdf.corr(method=method)
    elif method == "spearman":
        corrdf = inputdf.rank().corr(method="pearson")
    else:
        raise ValueError(
            f"Correlation method {method} is invalid. "
            "Available methods are 'pearson' and 'spearman'"
        )
    return corrdf.reindex(corrdf[response].abs().sort_values().index)


def make_correlation_plot(series, response, theme, corr_method):
    """Make Plotly trace for correlation plot"""
    xaxis_range = max(abs(series.values)) * 1.1
    layout = {
        "barmode": "relative",
        "margin": {"l": 200, "r": 50, "b": 20, "t": 100},
        "xaxis": {"range": [-xaxis_range, xaxis_range]},
        "title": f"Correlations ({corr_method}) between {response} and input parameters",
    }
    layout = theme.create_themed_layout(layout)

    return {
        "data": [
            {"x": series.values, "y": series.index, "orientation": "h", "type": "bar"}
        ],
        "layout": layout,
    }


def make_distribution_plot(df, parameter, response, theme):
    """Make plotly traces for scatterplot and histograms for selected
    response and input parameter"""

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
    scatter_trace, trendline = create_figure(
        plot_type="scatter",
        data_frame=df,
        x=parameter,
        y=response,
        trendline="ols",
        hover_data={"REAL": True},
        color_discrete_sequence=["SteelBlue"],
        marker={"size": 20, "opacity": 0.7},
    ).data

    fig.add_trace(scatter_trace, 1, 1)
    fig.add_trace(trendline, 1, 1)
    fig.add_trace(
        {
            "type": "histogram",
            "x": df[parameter],
            "showlegend": False,
        },
        3,
        1,
    )
    fig.add_trace(
        {
            "type": "histogram",
            "x": df[response],
            "showlegend": False,
        },
        3,
        2,
    )
    fig["layout"].update(
        theme_layout(
            theme.plotly_theme,
            {
                "bargap": 0.05,
                "xaxis": {
                    "title": parameter,
                },
                "yaxis": {"title": response},
                "xaxis2": {"title": parameter},
                "xaxis3": {"title": response},
                "title": f"Distribution of {response} and {parameter}",
            },
        )
    )

    return fig


def make_range_slider(domid, values, col_name):
    try:
        values.apply(pd.to_numeric, errors="raise")
    except ValueError as exc:
        raise ValueError(
            f"Cannot calculate filter range for {col_name}. "
            "Ensure that it is a numerical column."
        ) from exc
    return wcc.RangeSlider(
        label=col_name,
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
