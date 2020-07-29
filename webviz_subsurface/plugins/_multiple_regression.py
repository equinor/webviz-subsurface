import warnings
from itertools import combinations
from pathlib import Path

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import numpy.linalg as la
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_table import DataTable
from dash_table.Format import Format
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore

<<<<<<< HEAD
from .._datainput.fmu_input import load_csv, load_parameters
from .._utils.response_aggregation import filter_and_sum_responses
=======
from .._datainput.fmu_input import load_parameters, load_csv, load_smry
from .._utils.ensemble_handling import filter_and_sum_responses
>>>>>>> f595c3d9f2897ce5fe7f65715a996fbc72106341


class MultipleRegression(WebvizPluginABC):
    """ Visualizes the results of multiple regression of parameters and a chosen response using \
forward selection to find the best fit.

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
* **`column_keys`:** (Optional) list of simulation vectors to include as responses when reading \
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
* **`parameter_ignore`:** List of parameters (columns in csv or simulation vectors) to ignore
* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.

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

!> Regression models break down when there are **duplicate or highly correlated parameters**. \
Please make sure to properly filter your inputs or the model will give answers that are misleading.

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

    # pylint:disable=too-many-arguments
    # pylint:disable=unused-argument
    # pylint:disable=unused-variable
    # pylint:disable=too-many-lines
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
        parameter_ignore: list = None,
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.response_ignore = response_ignore if response_ignore else None
        self.parameter_ignore = parameter_ignore if parameter_ignore else None
        self.column_keys = column_keys
        self.time_index = sampling
        self.aggregation = aggregation

        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. Either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "csv files" or '
                    '"ensembles and response_file".'
                )
            self.parameterdf = pd.read_parquet(self.parameter_csv)
            self.responsedf = pd.read_parquet(self.response_csv)

        elif ensembles:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.parameterdf = load_parameters(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
            if self.response_file:
                self.responsedf = load_csv(
                    ensemble_paths=self.ens_paths,
                    csv_file=response_file,
                    ensemble_set_name="EnsembleSet",
                )
            else:
                self.responsedf = load_smry(
                    ensemble_paths=self.ens_paths,
                    column_keys=self.column_keys,
                    time_index=self.time_index,
                )
                self.response_filters["DATE"] = "single"
        else:
            raise ValueError(
                'Incorrect arguments.\
                 Either provide "csv files" or "ensembles and response_file".'
            )
        self.check_runs()
        self.check_response_filters()
        if response_ignore:
            self.responsedf.drop(response_ignore, errors="ignore", axis=1, inplace=True)
        if response_include:
            self.responsedf.drop(
                self.responsedf.columns.difference(
                    ["REAL", "ENSEMBLE", *response_include, *list(response_filters.keys()),]
                ),
                errors="ignore",
                axis=1,
                inplace=True,
            )
        if parameter_ignore:
            self.parameterdf.drop(parameter_ignore, axis=1, inplace=True)

        self.theme = app.webviz_settings["theme"]
        self.parameterdf = self.parameterdf.loc[:,self.parameterdf.apply(pd.Series.nunique) != 1]
        self.set_callbacks(app)

    @property
    def tour_steps(self):
        """ Adding a "Guided tour" functionality """
        steps = [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard displaying the results of a multiple regression of parameters and "
                    "a chosen response using forward selection to limit the number of terms. "
                    "Interaction terms can be added, up to third order. Adjusted R-squared is "
                    "used as the criterion in the forward selection algorithm."
                ),
            },
            {
                "id": self.uuid("p-values-plot"),
                "content": (
                    "A plot showing the p-values for the parameters from the table ranked from "
                    "most significant to least significant (low to high). Bars are highlighted "
                    "when the p-values are less than 0.05, meaning that the terms are likely to "
                    "be significant. Otherwise the bars are colored gray."
                ),
            },
            {
                "id": self.uuid("coefficient-plot"),
                "content": (
                    "A plot showing the sign of the parameters' regression coefficient values by "
                    "arrows pointing up or down, illustrating a positive or a negative coefficient "
                    "respectively. An arrow is highlighted if the corresponding p-value is "
                    "statistically significant, that is, a p-value below 0.05. Arrows "
                    "corresponding to p-values above this level of significance are shown in gray."
                ),
            },
            {
                "id": self.uuid("table"),
                "content": (
                    "A table showing the p-values for a forward selected combination of "
                    "parameters for a chosen response."
                ),
            },
            {"id": self.uuid("ensemble"), "content": ("Select the active ensemble.")},
            {"id": self.uuid("responses"), "content": ("Select the active response.")},
            {
                "id": self.uuid("exclude-include"),
                "content": (
                    "Select which parameters to include in your model. Exclusive mode lets you "
                    "remove specific parameters from beeing considered in the model selection. "
                    "Subset mode lets you pick a subset of parameters to investigate. Parameters "
                    "included here are not guaranteed to be included in the output model."
                ),
            },
            {
                "id": self.uuid("interaction"),
                "content": (
                    "Select the depth of the interaction level. 'Off' allows only for the "
                    "parameters in their original state. '2 levels' allow for the product of two "
                    "original parameters. '3 levels' allow for the product of three original "
                    "parameters. This feature allows you to investigate possible feedback effects."
                ),
            },
            {
                "id": self.uuid("max-params"),
                "content": (
                    "Choose the maximum number of parameters to include in your model. If "
                    "interaction is active, the number of included parameters is the selected "
                    "value here plus the interaction level. This is to make sure the interaction "
                    "terms have an intuitive interpretation."
                ),
            },
            {
                "id": self.uuid("force-in"),
                "content": ("Select parameters to force into the model."),
            },
            {
                "id": self.uuid("submit-button"),
                "content": (
                    "Press this button to update the table and the plots based on the settings "
                    "above."
                ),
            },
        ]
        return steps

    @property
    def responses(self):
        """ Returns valid responses. Filters out non numerical and filterable columns. """
        responses = list(
            self.responsedf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return [p for p in responses if p not in self.response_filters.keys()]

    @property
    def parameters(self):
        """ Returns numerical input parameters """
        parameters = list(
            self.parameterdf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return parameters

    @property
    def ensembles(self):
        """ Returns list of ensembles """
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def colors(self):
        """Dictionary of colors that are frequently used"""
        fig = go.Figure().to_dict()
        fig["layout"] = self.theme.create_themed_layout(fig["layout"])
        return {
            "default color": fig["layout"]["colorway"][0],
            "gray": "#606060",
            "dark gray": "#303030",
            "default text": fig["layout"]["template"]["layout"]["font"]["color"],
        }

    def check_runs(self):
        """ Check that input parameters and response files have
        the same number of runs """
        for col in ["ENSEMBLE", "REAL"]:
            if sorted(list(self.parameterdf[col].unique())) != sorted(
                list(self.responsedf[col].unique())
            ):
                raise ValueError("Parameter and response files have different runs")

    def check_response_filters(self):
        """ Check that provided response filters are valid """
        if self.response_filters:
            for col_name, col_type in self.response_filters.items():
                if col_name not in self.responsedf.columns:
                    raise ValueError(f"{col_name} is not in response file")
                if col_type not in ["single", "multi", "range"]:
                    raise ValueError(f"Filter type {col_type} for {col_name} is not valid.")

    @property
    def filter_layout(self):
        """ Layout to display selectors for response filters """
        children = []
        for col_name, col_type in self.response_filters.items():
            values = list(self.responsedf[col_name].unique())
            if col_type == "multi":
                selector = wcc.Select(
                    id=self.uuid(f"filter-{col_name}"),
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                    size=min(20, len(values)),
                )
            elif col_type == "single":
                selector = dcc.Dropdown(
                    id=self.uuid(f"filter-{col_name}"),
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    multi=False,
                    clearable=False,
                )
            children.append(html.Div(children=[html.Label(col_name), selector,]))
        return children

    @property
    def control_layout(self):
        """ Layout to select e.g. iteration and response """
        return [
            html.Div(
                [
                    html.Div("Ensemble:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid("ensemble"),
                        options=[{"label": ens, "value": ens} for ens in self.ensembles],
                        clearable=False,
                        value=self.ensembles[0],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div("Response:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid("responses"),
                        options=[{"label": ens, "value": ens} for ens in self.responses],
                        clearable=False,
                        value=self.responses[0],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        "Parameters:",
                        style={
                            "font-weight": "bold",
                            "display": "inline-block",
                            "margin-right": "10px",
                        },
                    ),
                    dcc.RadioItems(
                        id=self.uuid("exclude-include"),
                        options=[
                            {"label": "Exclusive", "value": "exc"},
                            {"label": "Subset", "value": "inc"},
                        ],
                        value="exc",
                        labelStyle={"display": "inline-block"},
                        style={"fontSize": ".80em"},
                    ),
                    dcc.Dropdown(
                        id=self.uuid("parameter-list"),
                        options=[{"label": ens, "value": ens} for ens in self.parameters],
                        clearable=True,
                        multi=True,
                        placeholder="",
                        value=[],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            html.Div("Filters:", style={"font-weight": "bold"}),
            html.Div(children=self.filter_layout),
            html.Div(
                [
                    html.Div(
                        "Model settings:", style={"font-weight": "bold", "marginTop": "20px"},
                    ),
                    html.Div(
                        "Interaction", style={"display": "inline-block", "margin-right": "10px"},
                    ),
                    dcc.Slider(
                        id=self.uuid("interaction"),
                        min=0,
                        max=2,
                        step=None,
                        marks={0: "Off", 1: "2 levels", 2: "3 levels"},
                        value=0,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        "Max number of parameters",
                        style={"display": "inline-block", "margin-right": "10px"},
                    ),
                    dcc.Dropdown(
                        id=self.uuid("max-params"),
                        options=[
                            {"label": val, "value": val}
                            for val in range(1, min(10, len(self.parameterdf.columns)))
                        ],
                        clearable=False,
                        value=3,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        "Force in", style={"display": "inline-block", "margin-right": "10px"},
                    ),
                    dcc.Dropdown(
                        id=self.uuid("force-in"),
                        clearable=True,
                        multi=True,
                        placeholder="Select parameters to force in",
                        value=[],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            html.Div(
                style={"display": "grid"},
                children=[
                    html.Button(
                        id=self.uuid("submit-button"),
                        children="Update model",
                        style={
                            "background-color": "LightGray",
                            "cursor": "not-allowed",
                            "border": "none",
                        },
                        disabled=True,
                    )
                ],
            ),
        ]

    @property
    def layout(self):
        """ Main layout """
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(style={"flex": 1}, children=self.control_layout),
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            id=self.uuid("page-title"),
                            style={
                                "textAlign": "center",
                                "display": "grid",
                                "font-weight": "bold",
                                "fontSize": "1.3em",
                            },
                        ),
                        html.Div(children=[wcc.Graph(id=self.uuid("p-values-plot"))]),
                        html.Div(children=[wcc.Graph(id=self.uuid("coefficient-plot"))]),
                        html.Label(
                            "Table of parameters and their corresponding p-values",
                            style={
                                "fontSize": ".925em",
                                "color": self.colors["default text"],
                                "textAlign": "center",
                            },
                        ),
                        DataTable(
                            id=self.uuid("table"),
                            sort_action="native",
                            filter_action="native",
                            page_action="native",
                            page_size=10,
                            style_cell={"fontSize": ".80em"},
                        ),
                    ],
                ),
            ],
        )

    def get_callback_list(self, func):
        """ Returns a list with either Inputs or States for multiple regression callback """
        components = [
            func(self.uuid("exclude-include"), "value"),
            func(self.uuid("parameter-list"), "value"),
            func(self.uuid("ensemble"), "value"),
            func(self.uuid("responses"), "value"),
            func(self.uuid("force-in"), "value"),
            func(self.uuid("interaction"), "value"),
            func(self.uuid("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                components.append(func(self.uuid(f"filter-{col_name}"), "value"))
        return components

    @property
    def model_callback_states(self):
        """ List of states for multiple regression callback """
        return self.get_callback_list(State)

    @property
    def model_callback_inputs(self):
        """ List of states for multiple regression callback """
        inputs = self.get_callback_list(Input)
        inputs.insert(0, Input(self.uuid("submit-button"), "n_clicks"))
        return inputs

    def make_response_filters(self, filters):
        """ Returns a list of active response filters """
        filteroptions = []
        if filters:
            for i, (col_name, col_type) in enumerate(self.response_filters.items()):
                filteroptions.append({"name": col_name, "type": col_type, "values": filters[i]})
        return filteroptions

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("submit-button"), "disabled"),
                Output(self.uuid("submit-button"), "style"),
            ],
            self.model_callback_inputs,
        )
        def update_button(
            n_clicks,
            exc_inc,
            parameter_list,
            ensemble,
            response,
            force_in,
            interaction,
            max_vars,
            *filters,
        ):
            ctx = dash.callback_context
            if dash.callback_context.triggered[0]["value"] is None:
                raise PreventUpdate
            # if the triggered comp is the sumbit-button
            if ctx.triggered[0]["prop_id"].split(".")[0] == self.uuid("submit-button"):
                return (
                    True,
                    {"background-color": "LightGray", "cursor": "not-allowed", "border": "none"},
                )
            return (
                False,
                {"color": "white", "background-color": self.colors["default color"]},
            )

        @app.callback(
            Output(self.uuid("parameter-list"), "placeholder"),
            [Input(self.uuid("exclude-include"), "value")],
        )
        def update_placeholder(exc_inc):
            """ Callback to update placeholder text in exlude/subset mode """
            if exc_inc == "exc":
                return "Select parameters to exclude"
            return "Select parameters for subset"

        @app.callback(
            [Output(self.uuid("force-in"), "options"), Output(self.uuid("force-in"), "value"),],
            [
                Input(self.uuid("parameter-list"), "value"),
                Input(self.uuid("exclude-include"), "value"),
            ],
            [State(self.uuid("force-in"), "value"),],
        )
        def update_force_in(parameter_list, exc_inc, force_in):
            """ Callback to update options for force in """
            if dash.callback_context.triggered[0]["value"] is None:
                raise PreventUpdate
            if exc_inc == "exc":
                df = self.parameterdf.drop(columns=["ENSEMBLE", "REAL"] + parameter_list)
            elif exc_inc == "inc":
                df = self.parameterdf[parameter_list] if parameter_list else []

            fi_lst = list(df)
            options = [{"label": fi, "value": fi} for fi in fi_lst]
            # Add only valid parameters
            force_in_updated = []
            for param in force_in:
                if param in fi_lst:
                    force_in_updated.append(param)
            return options, force_in_updated

        @app.callback(
            [
                Output(self.uuid("table"), "data"),
                Output(self.uuid("table"), "columns"),
                Output(self.uuid("page-title"), "children"),
                Output(self.uuid("p-values-plot"), "figure"),
                Output(self.uuid("coefficient-plot"), "figure"),
            ],
            [Input(self.uuid("submit-button"), "n_clicks")],
            self.model_callback_states,
        )
        # pylint:disable=too-many-locals
        def _update_visualizations(
            n_clicks,
            exc_inc,
            parameter_list,
            ensemble,
            response,
            force_in,
            interaction,
            max_vars,
            *filters,
        ):
            """ Callback to update the model for multiple regression

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Fit model using forward stepwise regression, with or without interactions
            5. Generate table and plots
            """
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            if exc_inc == "exc":
                parameterdf = self.parameterdf.drop(parameter_list, axis=1)
            elif exc_inc == "inc":
                parameterdf = self.parameterdf[["ENSEMBLE", "REAL"] + parameter_list]

            parameterdf = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])

            if exc_inc == "inc" and not parameter_list:
                return (
                    [{"e": ""}],
                    [{"name": "", "id": "e"}],
                    "Please select parameters to be included in the model",
                    {
                        "layout": {
                            "title": "<b>Please select parameters to include in the model</b><br>"
                        }
                    },
                    {
                        "layout": {
                            "title": "<b>Please select parameters to include in the model</b><br>"
                        }
                    },
                )

            result = gen_model(
                df, response, force_in=force_in, max_vars=max_vars, interaction_degree=interaction,
            )
            if not result or result.model.fit().df_model == 0:
                return (
                    [{"e": ""}],
                    [{"name": "", "id": "e"}],
                    "Cannot calculate fit for given selection. Select a different "
                    "response or filter setting",
                    {
                        "layout": {
                            "title": "<b>Cannot calculate fit for given selection</b><br>"
                            "Select a different response or filter setting."
                        }
                    },
                    {
                        "layout": {
                            "title": "<b>Cannot calculate fit for given selection</b><br>"
                            "Select a different response or filter setting."
                        }
                    },
                )
            # Generate table
            table = result.model.fit().summary2().tables[1].drop("Intercept")
            table.drop(["Std.Err.", "Coef.", "t", "[0.025", "0.975]"], axis=1, inplace=True)
            table.index.name = "Parameter"
            table.reset_index(inplace=True)
            columns = [
                {"name": i, "id": i, "type": "numeric", "format": Format(precision=4),}
                for i in table.columns
            ]
            data = table.to_dict("rows")

            # Get p-values for plot
            p_sorted = result.pvalues.sort_values().drop("Intercept")

            # Get coefficients for plot
            coeff_sorted = result.params.sort_values(ascending=False).drop("Intercept")

            return (
                data,
                columns,
                f"Multiple regression with {response} as response",
                make_p_values_plot(p_sorted, self.theme, self.colors),
                make_arrow_plot(coeff_sorted, p_sorted, self.theme, self.colors),
            )

    def add_webvizstore(self):
        if self.parameter_csv and self.response_csv:
            return [
                (read_csv, [{"csv_file": self.parameter_csv,}],),
                (read_csv, [{"csv_file": self.response_csv,}],),
            ]
        return [
            (
                load_parameters,
                [{"ensemble_paths": self.ens_paths, "ensemble_set_name": "EnsembleSet",}],
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
            )
            if self.response_file
            else (
                load_smry,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "column_keys": self.column_keys,
                        "time_index": self.time_index,
                    }
                ],
            ),
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def gen_model(
    df: pd.DataFrame,
    response: str,
    max_vars: int = 9,
    force_in: list = None,
    interaction_degree: bool = False,
):
    """ Wrapper for model selection algorithm. """
    if interaction_degree:
        df = _gen_interaction_df(df, response, interaction_degree + 1)
    return forward_selected(data=df, resp=response, force_in=force_in, maxvars=max_vars)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def _gen_interaction_df(df: pd.DataFrame, response: str, degree: int = 2):
    newdf = df.copy()

    name_combinations = []
    for i in range(1, degree + 1):
        name_combinations += [
            " × ".join(combination)
            for combination in combinations(newdf.drop(columns=response).columns, i)
        ]
    for name in name_combinations:
        if name.split(" × "):
            newdf[name] = newdf.filter(items=name.split(" × ")).product(axis=1)
    return newdf


# pylint:disable=too-many-locals
def forward_selected(data: pd.DataFrame, resp: str, force_in: list = None, maxvars: int = 5):
    """ Forward model selection algorithm

        Returns Statsmodels RegressionResults object.
        The algortihm is a modified standard forward selection algorithm.
        The selection criterion chosen is adjusted R squared.
        See this link for more information about the algorithm:
        https://en.wikipedia.org/wiki/Stepwise_regression

        Steps of the algorithm:
        - Initialize values
        - While there are parameters left and the last model was the best model yet and the
        parameter limit isnt reached, for every parameter not chosen yet:
            1.  If it is an interaction parameter, add the base features to the model.
            2.  Create a model matrix, fit the model and calculate selection criterion for each
                remaining parameter.
            3.  Pick the best parameter and repeat with remaining parameters until we satisfy an
                exit condition.
            4.  Finally fit a Statsmodels regression and return the results.

        Exit conditions:
            - No parameters in remaining.
            - The last model was not the best model.
            - Hit cap on maximum parameters.
            - We are about to add more parameters than there are observations.
     """

    # Initialize values for use in algorithm (sst is the total sum of squares)
    response = data[resp].to_numpy(dtype="float32")
    # Check for constant response
    if np.all(response == response[0]):
        return None
    sst = np.sum((response - np.mean(response)) ** 2)
    remaining = set(data.columns).difference(set(force_in + [resp]))
    selected = force_in
    current_score, best_new_score = 0.0, 0.0
    while remaining and current_score == best_new_score and len(selected) < maxvars:
        scores_with_candidates = []
        for candidate in remaining:
            if " × " in candidate:
                current_model = (
                    selected.copy()
                    + [candidate]
                    + list(set(candidate.split(" × ")).difference(set(selected)))
                )
            else:
                current_model = selected.copy() + [candidate]
            parameters = data.filter(items=current_model).to_numpy(dtype="float64")
            num_parameters = parameters.shape[1]
            parameters = np.append(parameters, np.ones((len(response), 1)), axis=1)

            # Fit model
            try:
                beta = la.inv(parameters.T @ parameters) @ parameters.T @ response
            except la.LinAlgError:
                # This clause lets us skip singluar and other non-valid model matricies.
                continue

            if len(response) - num_parameters - 1 < 1:
                # The exit condition means adding this parameter would add more parameters than
                # observations. This causes infinite variance in the model so we return the current
                # best model

                model_df = data.filter(items=selected)
                model_df["Intercept"] = np.ones((len(response), 1))
                model_df["response"] = response

                return _model_warnings(model_df)

            f_vec = beta @ parameters.T
            ss_res = np.sum((f_vec - np.mean(response)) ** 2)

            r_2_adj = 1 - (1 - (ss_res / sst)) * (
                (len(response) - 1) / (len(response) - num_parameters - 1)
            )
            scores_with_candidates.append((r_2_adj, candidate))

        # If the best parameter is interactive, add all base features
        scores_with_candidates.sort(key=lambda x: x[0])
        best_new_score, best_candidate = scores_with_candidates.pop()
        if current_score < best_new_score:
            if " × " in best_candidate:
                for base_feature in best_candidate.split(" × "):
                    if base_feature in remaining:
                        remaining.remove(base_feature)
                    if base_feature not in selected:
                        selected.append(base_feature)

            remaining.remove(best_candidate)
            selected.append(best_candidate)
            current_score = best_new_score

    # Finally fit a statsmodel from the selected parameters
    model_df = data.filter(items=selected)
    model_df["Intercept"] = np.ones((len(response), 1))
    model_df["response"] = response
    return _model_warnings(model_df)


def _model_warnings(design_matrix: pd.DataFrame):
    with warnings.catch_warnings():
        # Handle warnings so the graphics indicate that the model failed for the current input.
        warnings.filterwarnings("error", category=RuntimeWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        try:
            model = sm.OLS(design_matrix["response"], design_matrix.drop(columns="response")).fit()
        except (RuntimeWarning) as error:
            print("error: ", error)
            return None
    return model


def make_p_values_plot(p_sorted, theme, colors):
    """ Make p-values plot """
    p_values = p_sorted.values
    parameters = p_sorted.index
    fig = go.Figure()
    fig.add_trace(
        {
            "x": [param.replace(" × ", "<br>× ") for param in parameters],
            "y": p_values,
            "type": "bar",
            "marker": {
                "color": [
                    colors["default color"] if val < 0.05 else colors["gray"] for val in p_values
                ]
            },
        }
    )
    fig.update_traces(
        hovertemplate=[
            "<b>Parameter:</b> "
            + str(param)
            + "<br>"
            + "<b>P-value:</b> "
            + str(format(pval, ".4g"))
            + "<extra></extra>"
            for param, pval in zip(parameters, p_values)
        ]
    )
    fig.add_shape(
        {
            "type": "line",
            "y0": 0.05,
            "y1": 0.05,
            "x0": -0.5,
            "x1": len(p_values) - 0.5,
            "xref": "x",
            "line": {"color": colors["dark gray"], "width": 1.5},
        }
    )
    fig.add_annotation(x=len(p_values) - 0.2, y=0.05, text="P-value<br>= 0.05", showarrow=False)
    fig = fig.to_dict()
    fig["layout"].update(
        barmode="relative",
        height=500,
        title=dict(
            text="P-values for the parameters. Value lower than 0.05 indicates "
            "statistical significance",
            x=0.5,
        ),
    )
    fig["layout"] = theme.create_themed_layout(fig["layout"])
    return fig


def make_arrow_plot(coeff_sorted, p_sorted, theme, colors):
    """ Make arrow plot for the coefficients """
    params_to_coefs = dict(coeff_sorted)
    p_values = p_sorted.values
    parameters = p_sorted.index
    coeff_vals = list(map(params_to_coefs.get, parameters))
    centre_dist = len(parameters) / 3

    # Array with len(parameters) points for the x-axis, centered about x=1, with domain [0, 2]
    x = (
        [1]
        if len(parameters) == 1
        else np.linspace(max(1 - centre_dist, 0), min(1 + centre_dist, 2), num=len(parameters),)
    )
    y = np.zeros(len(x))
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            opacity=0,
            marker=dict(
                color=(p_values < 0.05).astype(np.int),  # 0.05: upper limit for stat.sig. p-value
                colorscale=[(0, colors["gray"]), (1, colors["default color"])],
                cmin=0,
                cmax=1,
            ),
        )
    )
    fig.update_traces(
        hovertemplate=[
            "<b>Parameter:</b> "
            + str(param)
            + "<br>"
            + "<b>P-value:</b> "
            + str(format(pval, ".4g"))
            + "<extra></extra>"
            for param, pval in zip(parameters, p_values)
        ]
    )
    # Arrows are drawn and added to plot.
    # Parameters with positive coefficients have arrows pointing upwards, and vice versa.
    for i, sign in enumerate(np.sign(coeff_vals)):
        x_coordinate = x[i]
        fig.add_shape(
            type="path",
            path=f" M {x_coordinate-0.025} 0 "
            f" L {x_coordinate-0.025} {sign*0.06} "
            f" L {x_coordinate-0.07} {sign*0.06} "
            f" L {x_coordinate} {sign*0.08} "
            f" L {x_coordinate+0.07} {sign*0.06} "
            f" L {x_coordinate+0.025} {sign*0.06} "
            f" L {x_coordinate+0.025} 0 ",
            fillcolor=colors["default color"] if p_values[i] < 0.05 else colors["gray"],
            line_width=0,
        )
    fig.add_shape(
        type="line",
        x0=-0.1,
        y0=0,
        x1=2 + 0.1,
        y1=0,
        line=dict(color=colors["dark gray"], width=1.5),
    )
    fig.add_shape(
        type="path",
        path=f" M {2+0.12} 0 L {2+0.1} -0.0035 L {2+0.1} 0.0035 Z",
        line_color=colors["dark gray"],
        line_width=1.5,
    )
    # Description of horisontal axis, placed 0.35 units rightwards from end of plot domain.
    fig.add_annotation(x=2 + 0.35, y=0, text="Increasing<br>p-value", showarrow=False)
    fig = fig.to_dict()
    fig["layout"].update(
        barmode="relative",
        height=500,
        title=dict(
            text="Parameters impact (increase or decrese) on response and their significance", x=0.5
        ),
        yaxis=dict(range=[-0.08, 0.08], title="", showticklabels=False),  # 0.08: arrow height
        xaxis=dict(
            title="", ticktext=[param.replace(" × ", "<br>× ") for param in parameters], tickvals=x,
        ),
    )
    fig["layout"] = theme.create_themed_layout(fig["layout"])
    return fig


def make_range_slider(domid, values, col_name):
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
        step=calculate_slider_step(
            min_value=values.min(), max_value=values.max(), steps=len(list(values.unique())) - 1,
        ),
        value=[values.min(), values.max()],
        marks={
            str(values.min()): {"label": f"{values.min():.2f}"},
            str(values.max()): {"label": f"{values.max():.2f}"},
        },
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)
