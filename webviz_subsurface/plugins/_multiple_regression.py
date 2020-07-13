from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
###from numba import njit, jit
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from dash_table import DataTable
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
from dash_table.Format import Format, Scheme
import webviz_core_components as wcc
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
from webviz_config.utils import calculate_slider_step
import statsmodels.formula.api as smf
import statsmodels.api as sm
from sklearn.preprocessing import PolynomialFeatures
import plotly.express as px

from .._datainput.fmu_input import load_parameters, load_csv

class MultipleRegression(WebvizPluginABC):
    """### Best fit using forward stepwise regression

This plugin shows a multiple regression of numerical input parameters and a chosen response.

Input can be given either as:

- Aggregated csv files for parameters and responses,
- An ensemble name defined in shared_settings and a local csv file for responses
stored per realizations.

**Note**: Non-numerical (string-based) input parameters and responses are removed.

**Note**: The response csv file will be aggregated per realization.

Arguments:

* `parameter_csv`: Aggregated csvfile for input parameters with 'REAL' and 'ENSEMBLE' columns.
* `response_csv`: Aggregated csvfile for response parameters with 'REAL' and 'ENSEMBLE' columns.
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
        parameter_filters: list = None
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.response_ignore = response_ignore if response_ignore else None
        self.column_keys = column_keys
        self.time_index = sampling
        self.aggregation = aggregation

        """Temporary way of filtering out non-valid parameters"""
        self.parameter_filters = [
            'RMSGLOBPARAMS:FWL', 'MULTFLT:MULTFLT_F1', 'MULTFLT:MULTFLT_F2',
            'MULTFLT:MULTFLT_F3', 'MULTFLT:MULTFLT_F4', 'MULTFLT:MULTFLT_F5', 
            'MULTZ:MULTZ_MIDREEK', 'INTERPOLATE_RELPERM:INTERPOLATE_GO',
            'INTERPOLATE_RELPERM:INTERPOLATE_WO', 'LOG10_MULTFLT:MULTFLT_F1', 
            'LOG10_MULTFLT:MULTFLT_F2', 'LOG10_MULTFLT:MULTFLT_F3',
            'LOG10_MULTFLT:MULTFLT_F4', 'LOG10_MULTFLT:MULTFLT_F5',
            'LOG10_MULTZ:MULTZ_MIDREEK', 'RMSGLOBPARAMS:COHIBA_MODEL_MODE',
            'COHIBA_MODEL_MODE']

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
            #self.parameterdf = read_csv(self.parameter_csv).drop(columns=self.parameter_filters)
            #self.responsedf = read_csv(self.response_csv)

            #For parquet files
            self.parameterdf = pd.read_parquet(self.parameter_csv).drop(columns=self.parameter_filters)
            self.responsedf = pd.read_parquet(self.response_csv)

        elif ensembles and response_file:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.parameterdf = load_parameters(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            ).drop(columns=self.parameter_filters)
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
                    "Dashboard displaying the results of a multiple "
                    "regression of input parameters and a chosen response."
                )
            },
            {
                "id": self.ids("table"),
                "content": (
                    "A table showing the results for the best combination of "
                    "parameters for a chosen response."
                )
            },
            {
                "id": self.ids("p-values-plot"),
                "content": (
                    "The p-values for the parameters from the table ranked from most significant "
                    "to least significant.  Red indicates "
                    "that the p-value is significant, gray indicates that the p-value "
                    "is not significant."
                )
            },
            {"id": self.ids("ensemble"), "content": ("Select the active ensemble."),},
            {"id": self.ids("responses"), "content": ("Select the active response."),},
            {"id": self.ids("max-params"), "content": ("Select the maximum number of parameters to be included in the regression."),},
            {"id": self.ids("force-out"), "content": ("Choose parameters to exclude in the regression."),},
            {"id": self.ids("force-in"), "content": ("Choose parameters to include in the regression."),},
            {"id": self.ids("interaction"), "content": ("Toggle interaction on/off between the parameters."),},
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
            domid = self.ids(f"filter-{col_name}")
            values = list(self.responsedf[col_name].unique())
            if col_type == "multi":
                selector = wcc.Select(
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                    size=min(20, len(values)),
                )
            elif col_type == "single":
                selector = dcc.Dropdown(
                    id=domid,
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    multi=False,
                    clearable=False,
                )
            else:
                return children
            children.append(html.Div(children=[html.Label(col_name), selector,]))

        return children

    @property
    def control_layout(self):
        """Layout to select e.g. iteration and response"""
        return [
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
            html.Div(
                [
                    html.Label("Max number of parameters"),
                    dcc.Dropdown(
                        id=self.ids("max-params"),
                        options=[
                            {"label": val, "value": val} for val in range(1,min(10,len(self.parameterdf.columns)))
                        ],
                        clearable=False,
                        value=3,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Force out"),
                    dcc.Dropdown(
                        id=self.ids("force-out"),
                        options=[
                            {"label": param,
                             "value": param} for param in self.parameters
                        ],
                        clearable=True,
                        multi=True,
                        value=[],
                        
                    )
                ]
            ),
            html.Div(
                [
                    html.Label("Force in"),
                    dcc.Dropdown(
                        id=self.ids("force-in"),
                        options=[
                            {"label": param,
                             "value": param} for param in self.parameters
                        ],
                        clearable=True,
                        multi=True,
                        value=[],
                        
                    )
                ]
            ),
            html.Div(
                [
                    html.Label("Interaction"),
                    dcc.RadioItems(
                        id=self.ids("interaction"),
                        options=[
                            {"label": "On", "value": True},
                            {"label": "Off", "value": False}
                        ],
                        value=True
                    )
                ]
            ),

        ]

    def make_button(self, id):
        return [
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateRows": "1fr 1fr",
                },
                children=[
                    html.Label("Press 'SUBMIT' to activate changes"),
                    html.Button(
                        id=id, 
                        children="Submit",
                    ),
                ],
            )
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            id=self.ids("table_title"),
                            style={"textAlign": "center"}
                        ),
                        DataTable(
                            id=self.ids("table"),
                            sort_action="native",
                            filter_action="native",
                            page_action="native",
                            page_size=10,
                            style_cell={"fontSize":14}
                        ),
                        html.Div(
                            style={'flex': 3},
                            children=[
                                wcc.Graph(id=self.ids('p-values-plot')),
                                dcc.Store(id=self.ids("initial-parameter"))
                            ]
                        ),
                        html.Div(
                            style={'flex': 3},
                            children=[
                                wcc.Graph(id=self.ids('coefficient-plot-S')),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 1},
                    children=self.control_layout + self.filter_layout + self.make_button(self.ids("submit-btn"))
                    if self.response_filters
                    else [],
                ),
            ],
        )

    @property
    def table_state_callbacks(self):
        """List of States for multiple regression table callback"""
        callbacks = [
            State(self.ids("ensemble"), "value"),
            State(self.ids("responses"), "value"),
            State(self.ids("force-out"), "value"),
            State(self.ids("force-in"), "value"),
            State(self.ids("interaction"), "value"),
            State(self.ids("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(State(self.ids(f"filter-{col_name}"), "value"))
        return callbacks
    
    @property
    def pvalues_state_callbacks(self):
        """List of States for p-values callback"""
        callbacks = [
            State(self.ids("ensemble"), "value"),
            State(self.ids("responses"), "value"),
            State(self.ids("force-out"), "value"),
            State(self.ids("force-in"), "value"),
            State(self.ids("interaction"), "value"),
            State(self.ids("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(State(self.ids(f"filter-{col_name}"), "value"))
        return callbacks
    
    @property
    def coefficientplot_state_callbacks(self):
        """List of states for coefficient plot callback"""
        callbacks = [
            State(self.ids("ensemble"), "value"),
            State(self.ids("responses"), "value"),
            State(self.ids("force-out"), "value"),
            State(self.ids("force-in"), "value"),
            State(self.ids("interaction"), "value"),
            State(self.ids("max-params"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(State(self.ids(f"filter-{col_name}"), "value"))
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
        """Set callbacks for the table, p-values plot, and arrow plot"""
        ###@njit()
        @app.callback(
            [
                Output(self.ids("table"), "data"),
                Output(self.ids("table"), "columns"),
                Output(self.ids("table_title"), "children"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.table_state_callbacks,
        )
        def _update_table(n_clicks, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
            """Callback to update datatable

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Fit model
            4. Fit model using forward stepwise regression, with or without interactions
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
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            
            #Get results and genereate datatable 
            result = gen_model(df, response, force_in = force_in, max_vars = max_vars, interaction= interaction)
            table = result.model.fit().summary2().tables[1].drop("Intercept")
            table.drop(["Std.Err.","t","[0.025","0.975]"],axis=1,inplace=True)
            
            #Turn index names (the params) into columms 
            table.index.name = "Parameter"
            table.reset_index(inplace=True)
            
            columns = [{"name": i, "id": i, 'type': 'numeric', "format": Format(precision=4)} for i in table.columns]
            data = table.to_dict("rows")

            if result.model.fit().df_model == 0:
                return (
                    [{"e": "Cannot calculate fit for given selection. Select a different response or filter setting"}],
                    [{"name": "Error", "id": "e"}],
                    "Error",
                )
            else:
                return(
                    data,
                    columns,
                    f"Multiple regression with {response} as response",
                )

        ###@njit()
        @app.callback(
            [
                Output(self.ids("p-values-plot"), "figure"),
                Output(self.ids("initial-parameter"), "data"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.pvalues_state_callbacks
        )
        def update_pvalues_plot(n_clicks, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
            """Callback to update the p-values plot
            
            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Fit model using forward stepwise regression, with or without interactions
            5. Get p-values from fitted model and sort them in ascending order
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
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            
            #Get results and generate p-values plot
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            result = gen_model(df, response, force_in = force_in, max_vars = max_vars, interaction = interaction)
            p_sorted = result.pvalues.sort_values().drop("Intercept")
            
            return make_p_values_plot(p_sorted, self.plotly_theme), p_sorted.index[-1]
        
        ###@njit()
        @app.callback(
            [
                Output(self.ids("coefficient-plot-S"), "figure"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.coefficientplot_state_callbacks
        )
        def update_coefficient_plot(n_clicks, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
            """Callback to update the coefficient plot"""
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            
            #Get results and generate coefficient plot
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            result = gen_model(df, response, force_in=force_in, max_vars=max_vars, interaction=interaction)
            model = result.params.sort_values().drop("Intercept").items()
            
            return make_arrow_plot(model, self.plotly_theme)
    
    ###@njit()
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
        force_in: [],
        max_vars: int=9,
        interaction: bool=False):
        
        """Genereates model with best fit"""
        if interaction:
            df = gen_interaction_df(df, response)
            return forward_selected_interaction(df, response, force_in = force_in, maxvars=max_vars)
        else:
            return forward_selected(df, response, force_in = force_in, maxvars=max_vars)

def gen_interaction_df(
    df: pd.DataFrame,
    response: str,
    degree: int=2,
    inter_only: bool=False,
    bias: bool=False):
    
    """Generates dataframe with interaction-terms"""
    x_interaction = PolynomialFeatures(
        degree=2,
        interaction_only=inter_only,
        include_bias=False).fit_transform(df.drop(columns=response))
    interaction_df = pd.DataFrame(
        x_interaction,
        columns=gen_column_names(
            df.drop(columns=response),
            inter_only))
    return interaction_df.join(df[response])

def gen_column_names(df, interaction_only):
    """Generate coloumn names. Specifically used to create interaction-term names"""
    output = list(df.columns)
    if interaction_only:
        for colname1 in df.columns:
            for colname2 in df.columns:
                if (
                    (colname1 != colname2) and
                    (f"{colname1}:{colname2}" not in output) or
                    (f"{colname2}:{colname1}" not in output)
                        ):
                        output.append(f"{colname1}:{colname2}")
    else:
        for colname1 in df.columns:
            for colname2 in df.columns:
                if (f"{colname1}:{colname2}" not in output) and (f"{colname2}:{colname1}" not in output):
                    output.append(f"{colname1}:{colname2}")
    return output

###@njit()
def forward_selected(data, response, force_in, maxvars=9):
    # TODO find way to remove non-significant variables form entering model. 
    """Linear model designed by forward selection.

    Parameters:
    -----------
    data : pandas DataFrame with all possible predictors and response

    response: string, name of response column in data

    Returns:
    --------
    model: an "optimal" fitted statsmodels linear model
        with an intercept
        selected by forward selection
        evaluated by adjusted R-squared
    """
    remaining = set(data.columns)
    remaining.remove(response)
    selected = force_in

    current_score, best_new_score = 0.0, 0.0
    while remaining and current_score == best_new_score and len(selected) < maxvars:
        scores_with_candidates = []
        for candidate in remaining:
            formula = "{} ~ {} + 1".format(response,
                                        ' + '.join(selected + [candidate]))
            score = smf.ols(formula, data).fit().rsquared_adj
            scores_with_candidates.append((score, candidate))
        scores_with_candidates.sort()
        best_new_score, best_candidate = scores_with_candidates.pop()
        if current_score < best_new_score:
            remaining.remove(best_candidate)
            selected.append(best_candidate)
            current_score = best_new_score
    formula = "{} ~ {} + 1".format(response,
                                ' + '.join(selected))
    model = smf.ols(formula, data).fit()
    return model

def forward_selected_interaction(data, response, force_in, maxvars=9):
    """Linear model designed by forward selection.

    Parameters:
    -----------
    data : pandas DataFrame with all possible predictors and response

    response: string, name of response column in data

    Returns:
    --------
    model: an "optimal" fitted statsmodels linear model
        with an intercept
        selected by forward selection
        evaluated by adjusted R-squared
    """
    remaining = set(data.columns)
    remaining.remove(response)
    selected = force_in
    current_score, best_new_score = 0.0, 0.0
    while remaining and current_score == best_new_score and len(selected) < maxvars:
        scores_with_candidates = []
        for candidate in remaining:
            formula = "{} ~ {} + 1".format(response,
                                        ' + '.join(selected + [candidate]))
            score = smf.ols(formula, data).fit().rsquared_adj
            scores_with_candidates.append((score, candidate))
        scores_with_candidates.sort()
        best_new_score, best_candidate = scores_with_candidates.pop()
        if current_score < best_new_score:
            candidate_split = best_candidate.split(sep=":")
            if len(candidate_split) == 2:  
                if candidate_split[0] not in selected and candidate_split[0] in remaining: 
                    remaining.remove(candidate_split[0])
                    selected.append(candidate_split[0])
                    maxvars += 1
                if candidate_split[1] not in selected and candidate_split[1] in remaining:
                    remaining.remove(candidate_split[1])
                    selected.append(candidate_split[1])
                    maxvars += 1
            remaining.remove(best_candidate)
            selected.append(best_candidate)
            current_score = best_new_score
    formula = "{} ~ {} + 1".format(response,
                                ' + '.join(selected))
    model = smf.ols(formula, data).fit()
    return model

def make_p_values_plot(p_sorted, theme):
    """Make Plotly trace for p-values plot"""
    p_values = p_sorted.values
    parameters = p_sorted.index

    fig = go.Figure()
    fig.add_trace(
        {
            "x": parameters,
            "y": p_values,
            "type": "bar",
            "marker":{"color": ["crimson" if val<0.05 else "#606060" for val in p_values]}
        }
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "barmode": "relative",
                "height": 500,
                "title": f"P-values for the parameters from the table"
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

def make_arrow_plot(model, theme):
    """Sorting dictionary in descending order. 
    Saving parameters and values of coefficients in lists.
    Saving plot-function to variable fig."""
    coefs = dict(sorted(model, key=lambda x: x[1], reverse=True))
    params = list(coefs.keys())
    vals = list(coefs.values())
    sgn = signs(vals)
    colors = color_array(vals, params, sgn)

    fig = arrow_plot(coefs, vals, params, sgn, colors, theme)
    #fig["layout"]["font"].update({"size": 12})

    return [fig] # Need hard brackets here

###@njit()
def signs(vals):
    """Saving signs of coefficients to array sgn"""
    sgn = np.zeros(len(vals))
    for i, v in enumerate(vals):
        sgn[i] = np.sign(v)
    return sgn

def arrow_plot(coefs, vals, params, sgn, colors, theme):
    """Making arrow plot to illutrate relative importance 
    of coefficients to a userdefined response"""
    steps = 2/(len(coefs)-1)
    points = len(coefs)

    x = np.linspace(0, 2, points)
    y = np.zeros(len(x))

    fig = px.scatter(x=x, y=y, opacity=0, color=sgn, color_continuous_scale=[(0.0, 'rgb(36, 55, 70)'), (0.125, 'rgb(102, 115, 125)'), (0.25, 'rgb(145, 155, 162)'), (0.375, 'rgb(189, 195, 199)'), (0.5, 'rgb(255, 231, 214)'), (0.625, 'rgb(216, 178, 189)'), (0.75, 'rgb(190, 128, 145)'), (0.875, 'rgb(164, 76, 101)'), (1.0, 'rgb(125, 0, 35)')], range_color=[-1, 1]) # Theme, replaced [] with () as hard brackets were rejected:(
    
    fig.update_layout(
        yaxis=dict(range=[-0.15, 0.15], title='', showticklabels=False), 
        xaxis=dict(range=[-0.2, x[-1]+0.2], title='', ticktext=[p for p in params], tickvals=[steps*i for i in range(points)]),
        autosize=False,
        coloraxis_colorbar=dict(
            title="",
            tickvals=[-0.97, -0.88, 0.88, 0.97],
            ticktext=["coefficient", "Great negative", "coefficient", "Great positive"],
            lenmode="pixels", len=300,
        ),
        hoverlabel=dict(
            bgcolor="white", 
        )
    )
    fig["layout"].update(
        theme_layout(
            theme,
            {
                "barmode": "relative",
                "height": 500,
                "title": f"Sign of coefficients for the parameters from the table"
            }
        )
    )
    fig["layout"]["font"].update({"size": 12})

    """Costumizing the hoverer"""
    fig.update_traces(hovertemplate='%{x}')

    """Adding arrows to figure"""
    for i, s in enumerate(sgn):
        if s == 1:
            fig.add_shape(
                type="path",
                path=f" M {x[i]-0.025} 0 L {x[i]-0.025} 0.06 L {x[i]-0.07} 0.06 L {x[i]} 0.08 L {x[i]+0.07} 0.06 L {x[i]+0.025} 0.06 L {x[i]+0.025} 0 ",
                line_color="#222A2A",
                fillcolor=colors[i], 
                line_width=0.6  
            )
        else:
            fig.add_shape(
                type="path",
                path=f" M {x[i]-0.025} 0 L {x[i]-0.025} -0.06 L {x[i]-0.07} -0.06 L {x[i]} -0.08 L {x[i]+0.07} -0.06 L {x[i]+0.025} -0.06 L {x[i]+0.025} 0 ",
                line_color="#222A2A",
                fillcolor=colors[i], 
                line_width=0.6
            )
    
    """Adding zero-line along y-axis"""
    fig.add_shape(
        # Line Horizontal
            type="line",
            x0=-0.18,
            y0=0,
            x1=x[-1]+0.18,
            y1=0,
            line=dict(
                color='#222A2A',
                width=0.75,
            ),
    )

    return fig # Should not have hard brackets here

def color_array(vals, params, sgn):
    """Function to scale coefficients to a green-red color range"""
    max_val = vals[0]
    min_val = vals[-1]

    standard = 250

    """Defining color values to match theme because I'm 
    lacking knowledge on how to live life with ease"""
    # Final RGB values
    rf = 36
    gf = 55
    bf = 70

    # Max RGB values
    r0 = 255
    g0 = 231
    b0 = 214

    # Initial RGB value
    ri = 125
    gi = 0
    bi = 35

    color_arr = ['rgba(255, 255, 255, 1)']*len(params)
    
    k = 0
    """Adding colors matching scaled values of coefficients to color_arr array"""
    for s, v in zip(sgn, vals):
        if s == 1:
            scaled_val_max = v/max_val
            color_arr[k] = f'rgba({int(ri*(scaled_val_max)+r0*(1-scaled_val_max))}, {int(int(gi*(scaled_val_max)+g0*(1-scaled_val_max)))}, {int(bi*(scaled_val_max)+b0*(1-scaled_val_max))}, 1)'
        else:
            scaled_val_min = v/min_val
            color_arr[k] = f'rgba({int(r0*(1-scaled_val_min)+rf*(scaled_val_min))}, {int(g0*(1-scaled_val_min)+gf*(scaled_val_min))}, {int(b0*(1-scaled_val_min)+bf*(scaled_val_min))}, 1)'
        k += 1
    
    return color_arr

###@njit()
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


###@njit()
@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)
