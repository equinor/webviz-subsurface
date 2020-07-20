import warnings
import time
from pathlib import Path
from itertools import combinations

import numpy as np
import numpy.linalg as la
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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

class MultipleRegression(WebvizPluginABC):
    """### Best fit using forward stepwise regression

This plugin shows a multiple regression of numerical parameters and a response.

Input can be given either as:

- Aggregated csv files for parameters and responses,
- An ensemble name defined in shared_settings and a local csv file for responses
stored per realizations.

**Note**: Non-numerical (string-based) input parameters and responses are removed.

**Note**: The response csv file will be aggregated per realization.

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
                    "illustrating a positive and/or negative coefficient respectively. " #Tung setning?
                    "An arrow is red if the corresponding p-value is significant, that is, a p-value below 0.05. "
                    "Arrows corresponding to p-values above this level of significance, are shown in gray."
                )
            },
            {"id": self.uuid("ensemble"), "content": ("Select the active ensemble."), },
            {"id": self.uuid("responses"), "content": ("Select the active response."), },
            {"id": self.uuid("max-params"), "content": ("Select the maximum number of parameters to be included in the regression."), },
            {"id": self.uuid("force-in"), "content": ("Choose parameters to include in the regression."), },
            {"id": self.uuid("interaction"), "content": ("Toggle interaction on/off between the parameters."), },
            {"id": self.uuid("submit-btn"), "content": ("Click SUBMIT to update the table and the plots."), },
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
                    "display": "grid",
                    "gridTemplateRows": "1fr 1fr"
                },
                children=[
                    html.Div("Press 'SUBMIT' to activate changes"),
                    html.Button(
                        id=self.uuid("submit-btn"), 
                        children="Submit"
                    )
                ]
            ),
            html.Div(
                [
                    html.Div("Ensemble"),
                    dcc.Dropdown(
                        id=self.uuid("ensemble"),
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
                    html.Div("Response"),
                    dcc.Dropdown(
                        id=self.uuid("responses"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.responses
                        ],
                        clearable=False,
                        value=self.responses[0],
                    ),
                ]
            ),
            html.Div(
                children=self.filter_layout
            ),
            html.Div(
                [
                    html.Div("Interaction"),
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
                    html.Div("Max number of parameters"),
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
                   dcc.RadioItems(
                       id=self.uuid("exclude_include"),
                       options=[
                           {"label": "Exclude parameters", "value": "exc"},
                           {"label": "Only include parameters", "value": "inc"}
                       ],
                       value="exc",
                       labelStyle={'display': 'inline-block'}
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
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div("Force in", style={'display': 'inline-block', 'margin-right': '10px'}),
                    html.Abbr("\u24D8", title="Hello, I am hover-enabled helpful information"),
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
                                wcc.Graph(id=self.uuid('p-values-plot')),
                                dcc.Store(id=self.uuid("initial-parameter"))
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
                    #if self.response_filters
                    #else [],
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
                return "Smart exclude text goes here"
            elif exc_inc == 'inc':
                return 'Smart include text goes here'

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
                Output(self.uuid("initial-parameter"), "data"),
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
                    }, None,
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
                        }, None,
                        {
                            "layout": {
                                "title": "<b>Cannot calculate fit for given selection</b><br>"
                                "Select a different response or filter setting."
                            }
                        },
                    )  
                # Generate table
                table = result.model.fit().summary2().tables[1].drop("Intercept")
                table.drop(["Std.Err.", "t", "[0.025","0.975]"], axis=1, inplace=True)
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
                    make_p_values_plot(p_sorted, self.plotly_theme), p_sorted.index[-1],

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
                    if opt["name"] == "DATE" and isinstance(opt["values"], str):
                        df = df.loc[df["DATE"].astype(str) == opt["values"]]
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
def gen_model(
        df: pd.DataFrame,
        response: str,
        max_vars: int=9,
        force_in: list=[],
        interaction_degree: bool=False
    ):
    """Wrapper for model selection algorithm."""
    if interaction_degree:
        df = _gen_interaction_df(df, response, interaction_degree)
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
    """ Forward model selection algorithm """
    y = data[response].to_numpy(dtype="float32")
    n = len(y)
    onevec = np.ones((len(y), 1))
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
            X = data.filter(items=current_model).to_numpy(dtype="float32")
            p = X.shape[1]
            if n - p - 1 < 1:
                model_df = data.filter(items=selected)
                model_df["Intercept"] = onevec
                with warnings.catch_warnings():
                    warnings.filterwarnings('error', category=RuntimeWarning)
                    warnings.filterwarnings('ignore', category=UserWarning)
                    try:
                        model = sm.OLS(data[response], model_df).fit()
                        if np.isnan(model.rsquared_adj):
                            warnings.warn("adjusted R_2 is not a number",category=RuntimeWarning)
                    except (Exception, RuntimeWarning) as e:
                        print("error: ", e)
                        return None
                return model
            X = np.append(X, onevec, axis=1)
            try: 
                beta = la.inv(X.T @ X) @ X.T @ y
            except la.LinAlgError:
                continue
            f_vec = beta @ X.T
            SS_RES = np.sum((f_vec-y_mean) ** 2)
            R_2_adj = 1-(1 - (SS_RES / SST))*((n-1)/(n-p-1))
            scores_with_candidates.append((R_2_adj, candidate))
         #   print("SWC:", scores_with_candidates[-1])
        #print("HERE")
        #print(scores_with_candidates)
        
        #print("sortedarr", scores_with_candidates.sort(key=lambda x: x[0]))
        scores_with_candidates.sort(key=lambda x: x[0])
        #print("scores_with_candidates", scores_with_candidates)
        best_new_score, best_candidate = scores_with_candidates.pop()
        #print("best_cand",best_candidate, best_new_score)
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
    model_df = data.filter(items=selected)
    model_df["Intercept"] = onevec
    
    with warnings.catch_warnings():
        warnings.filterwarnings('error', category=RuntimeWarning)
        warnings.filterwarnings('ignore', category=UserWarning)
        try:
            model = sm.OLS(data[response], model_df).fit()
            if np.isnan(model.rsquared_adj):
                warnings.warn("adjusted R_2 is not a number",category=RuntimeWarning)
        except (Exception, RuntimeWarning) as e:
            print("error: ", e)
    return model

def make_p_values_plot(p_sorted, theme):
    """Make p-values plot"""
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
                "title": f"P-values for the parameters, value lower than 0.05 is statistically significant"
            }
        )
    )
    fig.add_shape(
        {
            "type": "line", 
            "y0": 0.05, "y1": 0.05, "x0": -0.5, "x1": len(p_values)-0.5, "xref": "x",
            "line": {"color": "#303030", "width": 1.5}
        }
    )
    fig["layout"]["font"].update({"size": 12})
    return fig

def make_arrow_plot(coeff_sorted, p_sorted, theme):
    """Make arrow plot for the coefficients"""
    params_to_coefs = dict(coeff_sorted)
    p_values = p_sorted.values
    parameters = p_sorted.index
    coeff_vals = list(map(params_to_coefs.get, parameters))
    sgn = np.sign(coeff_vals)

    steps = 2/(len(parameters)-1) if len(parameters) > 1 else 0
    num_arrows = len(parameters)
    x = np.linspace(0, 2, num_arrows) if num_arrows > 1 else np.linspace(0, 2, 3)
    y = np.zeros(len(x))

    fig = px.scatter(x=x, y=y, opacity=0)
    
    fig.update_layout(
        yaxis=dict(range=[-0.15, 0.15], title='', 
                   showticklabels=False), 
        xaxis=dict(range=[-0.23, x[-1]+0.23], 
                   title='', 
                   ticktext=[param.replace("×", "<br>× ") for param in parameters], 
                   tickvals=[steps*i for i in range(num_arrows)] if num_arrows>1 else [1]),
        hoverlabel=dict(
            bgcolor="white", 
        )
    )
    fig.add_annotation(
        x=-0.23,
        y=0,
        text="Small <br>p-value",
        showarrow=False
    )
    fig.add_annotation(
        x=x[-1]+0.23,
        y=0,
        text="Great <br>p-value",
        showarrow=False
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "barmode": "relative",
                "height": 500,
                "title": "Parameters impact (increase " #Usikker på tittel (særlig det i parentes)
                         "or decrese) on response and "
                         "their significance"
            }
        )
    )
    fig["layout"]["font"].update({"size": 12})

    """Customizing the hoverer"""
    fig.update_traces(hovertemplate='%{x}')

    """Adding arrows to figure"""
    for i, s in enumerate(sgn):
        xx = x[i] if num_arrows > 1 else x[1]
        fig.add_shape(
            type="path",
            path=f" M {xx-0.025} 0 " \
                 f" L {xx-0.025} {s*0.06} " \
                 f" L {xx-0.07} {s*0.06} " \
                 f" L {xx} {s*0.08} " \
                 f" L {xx+0.07} {s*0.06} " \
                 f" L {xx+0.025} {s*0.06} " \
                 f" L {xx+0.025} 0 ",
            fillcolor="crimson" if p_values[i] < 0.05 else "#606060",
            line_width=0
        )
    """Adding zero-line along y-axis"""
    fig.add_shape(
        type="line",
        x0=-0.1,
        y0=0,
        x1=x[-1]+0.1,
        y1=0,
        line=dict(
            color='#222A2A',
            width=0.75,
        ),
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
