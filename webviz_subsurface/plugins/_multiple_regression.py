import warnings
import time
from pathlib import Path
from itertools import combinations

import numpy as np
import numpy.linalg as la
import pandas as pd
import plotly.graph_objects as go
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import dash_bootstrap_components as dbc
import statsmodels.api as sm
from dash_table import DataTable
from dash.dependencies import Input, Output, State
from dash_table.Format import Format, Scheme
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
from webviz_config.utils import calculate_slider_step
from sklearn.preprocessing import PolynomialFeatures

from .._datainput.fmu_input import load_parameters, load_csv
from .._utils.ensemble_handling import filter_and_sum_responses

class MultipleRegression(WebvizPluginABC):
    """### Best fit using forward stepwise regression

This plugin shows a multiple regression of numerical parameters and a response.

Input can be given either as:

- Aggregated csv files for parameters and responses,
- An ensemble name defined in shared_settings and a local csv file for responses
stored per realizations.

**Note**: Non-numerical (string-based) input parameters and responses are removed.

**Note**: The response csv file will be aggregated per realization.

**Note**: Regression models break down when there are duplicate or highly correlated parameters,
please make sure to properly filter your inputs as the model will give a response, but it will be wrong.

Arguments:

* `parameter_csv`: Aggregated csvfile for input parameters with 'REAL' and 'ENSEMBLE' columns.
* `response_csv`: Aggregated csvfile for response with 'REAL' and 'ENSEMBLE' columns.
* `ensembles`: Which ensembles in `shared_settings` to visualize. If neither response_csv or
            response_file is defined, the definition of ensembles implies that you want to
            use simulation timeseries data directly from UNSMRY data. This also implies that
            the date will be used as a response filter of type `single`.
* `response_file`: Local (per realization) csv file for response parameters.
* `response_filters`: Optional dictionary of responses (columns in csv file) that can be used
as row filtering before aggregation. (See below for filter types).
* `response_ignore`: Response (columns in csv) to ignore (cannot use with response_include).
* `response_include`: Response (columns in csv) to include (cannot use with response_ignore).
* `column_keys`: Simulation vectors to use as responses read directly from UNSMRY-files in the
                defined ensembles using fmu-ensemble (cannot use with response_file,
                response_csv or parameters_csv).
* `sampling`: Sampling frequency if using fmu-ensemble to import simulation time series data.
            (Only relevant if neither response_csv or response_file is defined). Default monthly
* `aggregation`: How to aggregate responses per realization. Either `sum` or `mean`.
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
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
        parameter_ignore: list = None,
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
                'Incorrent argument. either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "csv files" or '
                    '"ensembles and response_file".'
                )
            #For csv files
            #self.parameterdf = read_csv(self.parameter_csv)
            #self.responsedf = read_csv(self.response_csv)

            #For parquet files
            self.parameterdf = pd.read_parquet(self.parameter_csv)
            self.responsedf = pd.read_parquet(self.response_csv)

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
                'Incorrect arguments.\
                 Either provide "csv files" or "ensembles and response_file".'
            )
        self.check_runs()
        self.check_response_filters()
        if response_ignore:
            self.responsedf.drop(
                response_ignore,
                errors="ignore", axis=1, inplace=True)
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
        if parameter_ignore:
            self.parameterdf.drop(parameter_ignore, axis=1, inplace=True)

        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uuid}"

    @property
    def tour_steps(self):
        steps = [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard displaying the results of a multiple "
                    "regression of input parameters and a chosen response."
                )
            },
            {
                "id": self.uuid("table"),
                "content": (
                    "A table showing the results for the best combination of "
                    "parameters for a chosen response."
                )
            },
            {
                "id": self.uuid("p-values-plot"),
                "content": (
                    "A plot showing the p-values for the parameters from the table ranked from most significant "
                    "to least significant.  Red indicates "
                    "that the p-value is significant, gray indicates that the p-value "
                    "is not significant."
                )
            },
            {
                "id": self.uuid("coefficient-plot"),
                "content": (
                    "A plot showing the sign of parameters' coefficient values by arrows pointing up and/or down, "
                    "illustrating a positive and/or negative coefficient respectively. "
                    "An arrow is red if the corresponding p-value is significant, that is, a p-value below 0.05. "
                    "Arrows corresponding to p-values above this level of significance, are shown in gray."
                )
            },
            {"id": self.uuid("submit-btn"), "content": ("Press this button to update the table and the plots based on the options below."), },
            {"id": self.uuid("ensemble"), "content": ("Select the active ensemble."), },
            {"id": self.uuid("responses"), "content": ("Select the active response."), },
            {"id": self.uuid("exclude_include"), "content": (
                "Choose between using all availabe parameters or a subset of the available parameters in the regression. "
                "If all parameters are chosen it is possible to exclude some the parameters by choosing them from the drop down menu."
                ), 
            },
            {"id": self.uuid("interaction"), "content": ("Select the desired level of interaction in the visualized model."), },
            {"id": self.uuid("max-params"), "content": ("Select the maximum number of parameters to be included in the visualized model."), },
            {"id": self.uuid("force-in"), "content": ("Select parameters forced to be included in the visualized model."), },
        ]
        return steps

    @property
    def responses(self):
        """Returns valid responses. Filters out non numerical columns,
        and filterable columns. Replaces : and , with _ to make it work with the model"""
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
        """Layout to select e.g. iteration and response"""
        return [
            html.Div(
                style={
                    "display": "grid"
                },
                children=[
                    html.Button(
                        id=self.uuid("submit-btn"), 
                        children="Press to update model",
                        style={"marginBottom": "12px"}
                    )
                ]
            ),
            html.Div(
                [
                    html.Div("Ensemble:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid("ensemble"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.ensembles
                        ],
                        clearable=False,
                        value=self.ensembles[0],
                        style={"marginBottom": "20px"}
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div("Response:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid("responses"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.responses
                        ],
                        clearable=False,
                        value=self.responses[0],
                        style={"marginBottom": "20px"}
                    ),
                ]
            ),
            html.Div(
                [
                   html.Div("Parameters:", style={"font-weight": "bold", 'display': 'inline-block', 'margin-right': '10px'}),
                   html.Abbr("\u24D8", title="""This lets your control what parameters to include in your model.
There are two modes, inclusive and exclusive:
- Exclusive mode:
    Lets you remove spesific parameters from your model.

- Inclusive mode:
    Lets you pick a subset of parameters to investigate.
    Parameters included here are not
    guaranteed to be included in the output model.
"""
                    ),
                   dcc.RadioItems(
                       id=self.uuid("exclude_include"),
                       options=[
                           {"label": "Exclude from full set", "value": "exc"},
                           {"label": "Make a subset", "value": "inc"}
                       ],
                       value="exc",
                       labelStyle={'display': 'inline-block'},
                       style = {'fontSize': ".80em"},
                   )
               ]
            ),
            html.Div(
                [
                    dcc.Dropdown(
                        id=self.uuid("parameter-list"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.parameters
                        ],
                        clearable=True,
                        multi=True,
                        placeholder="",
                        value=[],
                        style={"marginBottom": "20px"}
                    ),
                ]
            ),
            html.Div("Filters:", style={"font-weight": "bold"}),
            html.Div(children=self.filter_layout),
            html.Div(
                [
                    html.Div("Model settings:", style={"font-weight": "bold", "marginTop": "20px"}),
                    html.Div("Interaction", style={ 'display': 'inline-block', 'margin-right': '10px'}),
                    html.Abbr("\u24D8", title="""This slider lets your select how deep your interaction is.
Off allows only for the parameters in their original state.
2 levels allows for the product of 2 original parameters.
3 levels allows for the product of 3 original parameters.
This feature allows you to investigate possible feedback effects.
                    """),
                    dcc.Slider(
                        id=self.uuid("interaction"),
                        min=0,
                        max=2,
                        step=None,
                        marks={
                            0: "Off",
                            1: "2 levels",
                            2: "3 levels"
                        },
                        value=0
                    )
                ]
            ),
            html.Div(
                [
                    html.Div("Max number of parameters", style={'display': 'inline-block', 'margin-right': '10px'}),
                    html.Abbr("\u24D8", title="""Lets you put a cap on the number of parameters to include in your model
If interaction is active cap is the selected value + interaction level.
This is to make sure the interaction terms have an intuitive interpretation.
"""),
                    dcc.Dropdown(
                        id=self.uuid("max-params"),
                        options=[
                            {"label": val, "value": val} for val in range(1, min(10, len(self.parameterdf.columns)))
                        ],
                        clearable=False,
                        value=3,
                    ),
                ]
            ),
            html.Div(
                [
                   html.Div("Force in", style={'display': 'inline-block', 'margin-right': '10px'}),
                    html.Abbr("\u24D8", title="""This lets you force parameters into the model, 
parameters here are guaranteed to appear in the model.
"""),
                    dcc.Dropdown(
                        id=self.uuid("force-in"),
                        clearable=True,
                        multi=True,
                        placeholder='Describe force-in here',
                        value=[],

                    )
                ]
            ),
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            id=self.uuid("table_title"),
                            style={"textAlign": "center"}
                        ),
                        DataTable(
                            id=self.uuid("table"),
                            sort_action="native",
                            filter_action="native",
                            page_action="native",
                            page_size=10,
                            style_cell={"fontSize": ".80em"}
                        ),
                        html.Div(
                            children=[
                                wcc.Graph(id=self.uuid('p-values-plot'))
                            ]
                        ),
                        html.Div(
                            children=[
                                wcc.Graph(id=self.uuid('coefficient-plot')),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 1},
                    children=self.control_layout
                )
            ]
        )
        
    @property
    def model_callback_states(self):
        """List of states for multiple regression callback"""
        states = [
            State(self.uuid("exclude_include"), "value"),
            State(self.uuid("parameter-list"), "value"),
            State(self.uuid("ensemble"), "value"),
            State(self.uuid("responses"), "value"),
            State(self.uuid("force-in"), "value"),
            State(self.uuid("interaction"), "value"),
            State(self.uuid("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                states.append(State(self.uuid(f"filter-{col_name}"), "value"))
        return states


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
        """Set callbacks for placeholder text for exc/inc dropdown"""
        @app.callback(
                Output(self.uuid("parameter-list"), "placeholder"),
                [Input(self.uuid("exclude_include"), "value")]
        )
        def update_placeholder(exc_inc):
            if exc_inc == 'exc':
                return "Choose parameters to exclude..."
            elif exc_inc == 'inc':
                return "Choose parameters for subset..."

        """Set callbacks for interaction between exclude/include param and force-in"""
        @app.callback(
            [
                Output(self.uuid("force-in"), "options"),
                Output(self.uuid("force-in"), "value")
            ],
            [
                Input(self.uuid("parameter-list"), "value"),
                Input(self.uuid("exclude_include"), "value"),
            ],
            [
                State(self.uuid("force-in"), "value"),
            ],
        )
        def update_force_in(parameter_list, exc_inc, force_in):
            """Returns a dictionary with options for force in"""
            #If exclusive and parameter_list empty -> all param avail. for force-in
            #If inclusive and parameter_list empty -> no param avail.
            if exc_inc == "exc":
                df = self.parameterdf.drop(columns=["ENSEMBLE", "REAL"] + parameter_list)
            elif exc_inc == "inc":
                df = self.parameterdf[parameter_list] if parameter_list else []

            fi_lst = list(df)
            options=[{"label": fi, "value": fi} for fi in fi_lst]
            for param in force_in:
                if param not in fi_lst:
                    force_in.remove(param)

            return options, force_in
        
        """Set callbacks for the table, p-values plot, and arrow plot"""
        @app.callback(
            [
                Output(self.uuid("table"), "data"),
                Output(self.uuid("table"), "columns"),
                Output(self.uuid("table_title"), "children"),
                Output(self.uuid("p-values-plot"), "figure"),
                Output(self.uuid("coefficient-plot"), "figure")
            ],
            [
                Input(self.uuid("submit-btn"), "n_clicks")
            ],
            self.model_callback_states,
        )
        def _update_visualizations(n_clicks, exc_inc, parameter_list, ensemble, response, force_in, interaction, max_vars, *filters):
            """Callback to update the model for multiple regression

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

            #If no selected parameters
            if exc_inc == "inc" and not parameter_list:
                return(
                    [{"e": ""}],
                    [{"name": "", "id": "e"}],
                    "Please select parameters to be included in the model",
                    {
                    "layout": {
                        "title": "<b>Please select parameters to be included in the model</b><br>"
                        }
                    },
                    {
                    "layout": {
                        "title": "<b>Please select parameters to be included in the model</b><br>"
                        }
                    },
                )
                
            else:
                # Get results from the model
                result = gen_model(df, response, force_in =force_in, max_vars=max_vars, interaction_degree=interaction)
                if not result:
                    return(
                        [{"e": ""}],
                        [{"name": "", "id": "e"}],
                        "Cannot calculate fit for given selection. Select a different response or filter setting",
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
                table.drop(["Std.Err.", "Coef.", "t", "[0.025","0.975]"], axis=1, inplace=True)
                table.index.name = "Parameter"
                table.reset_index(inplace=True)
                columns = [{"name": i, "id": i, 'type': 'numeric', "format": Format(precision=4)} for i in table.columns]
                data = table.to_dict("rows")

                # Get p-values for plot
                p_sorted = result.pvalues.sort_values().drop("Intercept")

                # Get coefficients for plot
                coeff_sorted = result.params.sort_values(ascending=False).drop("Intercept")

                return(
                    # Generate table
                    data,
                    columns,
                    f"Multiple regression with {response} as response",

                    # Generate p-values plot
                    make_p_values_plot(p_sorted, self.plotly_theme),

                    # Generate coefficient plot
                    make_arrow_plot(coeff_sorted, p_sorted, self.plotly_theme)
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
def gen_model(
        df: pd.DataFrame,
        response: str,
        max_vars: int=9,
        force_in: list=[],
        interaction_degree: bool=False
    ):
    """Wrapper for model selection algorithm."""
    if interaction_degree:
        df = _gen_interaction_df(df, response, interaction_degree+1)
        model = forward_selected(
            data=df,
            response=response,
            force_in=force_in,
            maxvars=max_vars
            )
    else:
        model = forward_selected(
            data=df,
            response=response,
            force_in=force_in,
            maxvars=max_vars
        ) 
    return model

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def _gen_interaction_df(
    df: pd.DataFrame,
    response: str,
    degree: int=4):
    newdf = df.copy()

    name_combinations = []
    degree += 1 
    for i in range(1, degree+1):
        name_combinations += [" × ".join(combination) for combination in combinations(newdf.drop(columns=response).columns, i)]
    for name in name_combinations:
        if name.split(" × "):
            newdf[name] = newdf.filter(items=name.split(" × ")).product(axis=1)
    return newdf

def forward_selected(data: pd.DataFrame,
                     response: str, 
                     force_in: list=[], 
                     maxvars: int=5):
    """ Forward model selection algorithm

        Return statsmodels RegressionResults object
        the algortihm is a modified standard forward selection algorithm. 
        The selection criterion chosen is adjusted R squared.
        See this link for more info on algorithm: 
        https://en.wikipedia.org/wiki/Stepwise_regression
     
        step by step of the algorithm:
        - initialize values
        - while there are parameters left and the last model was the best model yet and the parameter limit isnt reached
        - for every parameter not chosen yet.
            1. If it is an interaction parameter add the base features to the model.
            2. Create model matrix, fit model and calculate selection criterion, for each remaining parameter.
            3. pick the best parameter and repeat with remaining parameters until we satisfy an exit condition.
            4. finally fit a statsmodel regression and return the results. 
     
        Exit conditions:
            - no parameters in remaining.
            - the last model was not the best model
            - hit cap on maximum parameters.
            - we are about to add more parameters than there are observations.
     """


    # Initialize values for use in algorithm
    # y is the response, SST is the total sum of squares
    y = data[response].to_numpy(dtype="float32")
    n = len(y)
    y_mean = np.mean(y)
    SST = np.sum((y-y_mean) ** 2)
    remaining = set(data.columns).difference(set(force_in+[response]))
    selected = force_in
    current_score, best_new_score = 0.0, 0.0
    while remaining and current_score == best_new_score and len(selected) < maxvars:
        scores_with_candidates = []
        for candidate in remaining:
            if " × " in candidate:
                current_model = selected.copy() + [candidate] + list(set(candidate.split("*")).difference(set(selected)))
            else:
                current_model = selected.copy()+[candidate]
            X = data.filter(items=current_model).to_numpy(dtype="float64")
            p = X.shape[1]  
            X = np.append(X, np.ones((len(y), 1)), axis=1)

            # Fit model 
            try: 
                beta = la.inv(X.T @ X) @ X.T @ y
            except la.LinAlgError:
                # This clause lets us skip singluar and other non-valid model matricies.
                continue

            if n - p - 1 < 1: 
                
                # The exit condition means adding this parameter would add more parameters than observations, 
                # This causes infinite variance in the model so we return the current best model
                
                model_df = data.filter(items=selected)
                model_df["Intercept"] =  np.ones((len(y), 1))
                model_df["response"] = y
                
                return _model_warnings(model_df)

            f_vec = beta @ X.T
            SS_RES = np.sum((f_vec-y_mean) ** 2)
            
            R_2_adj = 1-(1 - (SS_RES / SST))*((n-1)/(n-p-1))
            scores_with_candidates.append((R_2_adj, candidate))
        
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
    model_df["Intercept"] =  np.ones((len(y), 1))
    model_df["response"]=y
    return _model_warnings(model_df)

def _model_warnings(design_matrix: pd.DataFrame):
    with warnings.catch_warnings():
        # Handle warnings so the graphics indicate explicity that the model failed for the current input. 
        warnings.filterwarnings('error', category=RuntimeWarning)
        warnings.filterwarnings('ignore', category=UserWarning)
        try:
            model = sm.OLS(design_matrix["response"], design_matrix.drop(columns="response")).fit()
        except (Exception, RuntimeWarning) as e:
            print("error: ", e)
            return None
    return model

def make_p_values_plot(p_sorted, theme):
    """Make p-values plot"""
    ###### Code for other theme thingy is tagged out ######
    p_values = p_sorted.values
    parameters = p_sorted.index
    fig = go.Figure()
    fig.add_trace(
        {
            "x": [param.replace(" × ", "<br>× ") for param in parameters],
            "y": p_values,
            "type": "bar",
            "marker":{"color": ["crimson" if val < 0.05 else "#606060" for val in p_values]}
        }
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "barmode": "relative",
                "height": 500,
                "title": f"P-values"
            }
        )
        #barmode = "relative",
        #height = 500,
        #title = f"P-values for the parameters. Value lower than 0.05 is statistically significant",
        #plot_bgcolor = "#fff"
    )
    fig.add_shape(
        {
            "type": "line", 
            "y0": 0.05, "y1": 0.05, "x0": -0.5, "x1": len(p_values)-0.5, "xref": "x",
            "line": {"color": "#303030", "width": 1.5}
        }
    )
    fig.add_annotation(
        x=len(p_values)-0.35,
        y=0.05,
        text="P-value<br>= 0.05",
        showarrow=False
    )
    fig["layout"]["font"].update({"size": 12})
    #fig["layout"] = theme.create_themed_layout(fig["layout"])
    return fig

def make_arrow_plot(coeff_sorted, p_sorted, theme):
    """Make arrow plot for the coefficients"""
    ###### Code for other theme thingy is tagged out ######
    params_to_coefs = dict(coeff_sorted)
    p_values = p_sorted.values
    parameters = p_sorted.index
    coeff_vals = list(map(params_to_coefs.get, parameters))

    centre = 1
    domain = 2
    steps = domain/(len(parameters)-1) if len(parameters) > 1 else 0
    centre_dist = len(parameters)/(domain+1)
    x = [1] if len(parameters)==1 else np.linspace(max(centre-centre_dist, 0), 
                                              min(centre+centre_dist, domain), 
                                              num=len(parameters))
    y = np.zeros(len(x))

    fig = go.Figure(go.Scatter(x=x, y=y, opacity=0))
    fig.update_layout(
        yaxis=dict(range=[-0.15, 0.15], title='',
                   showticklabels=False),
        xaxis=dict(range=[-0.23, domain+0.23],
                   title='',
                   ticktext=[param.replace("*", "*<br>") for param in parameters],
                   tickvals=[i for i in x]),
        #coloraxis_showscale=False,
        #autosize=True,
        hoverlabel=dict(bgcolor="lightgrey")
    )
    """Customizing the hoverer"""
    fig.update_traces(
        hovertemplate=[str(param) + '<br>' + str(format(pval, '.4g')) + '<extra></extra>' for param, pval in zip(parameters, p_values)]
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "barmode": "relative",
                "height": 500,
                "title": "Parameters impact (increase "
                         "or decrese) on response and "
                         "their significance"
            }
        )
        #barmode = "relative",
        #height = 500,
        #title = "Parameters impact (increase " #Usikker på tittel (særlig det i parentes)
        #        "or decrese) on response and "
        #        "their significance",
        #plot_bgcolor = "#fff"
    )
    fig["layout"]["font"].update({"size": 12})
    #fig["layout"] = theme.create_themed_layout(fig["layout"])

    """Adding arrows to figure"""
    for i, sign in enumerate(np.sign(coeff_vals)):
        x_coordinate = x[i]
        fig.add_shape(
            type="path",
            path=f" M {x_coordinate-0.025} 0 " \
                 f" L {x_coordinate-0.025} {sign*0.06} " \
                 f" L {x_coordinate-0.07} {sign*0.06} " \
                 f" L {x_coordinate} {sign*0.08} " \
                 f" L {x_coordinate+0.07} {sign*0.06} " \
                 f" L {x_coordinate+0.025} {sign*0.06} " \
                 f" L {x_coordinate+0.025} 0 ",
            fillcolor="crimson" if p_values[i] < 0.05 else "#606060",
            line_width=0
        )
    """Adding zero-line along y-axis"""
    fig.add_shape(
        type="line",
        x0=-0.1, y0=0, x1=domain+0.1, y1=0,
        line=dict(
            color='#222A2A',
            width=0.75,
        ),
    )
    fig.add_shape(
        type="path",
        path=f" M {domain+0.12} 0 L {domain+0.1} -0.005 L {domain+0.1} 0.005 Z",
        line_color="#222A2A",
        line_width=0.75,
    )
    fig.add_annotation(
        x=domain+0.23, y=0,
        text="Increasing<br>p-value",
        showarrow=False
    )
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
        }
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
