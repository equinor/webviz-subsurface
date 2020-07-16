from uuid import uuid4
from pathlib import Path

import warnings
import numpy as np
import pandas as pd
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
from itertools import combinations
import plotly.express as px
import numpy.linalg as la
from .._datainput.fmu_input import load_parameters, load_csv
import time
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
                    "A plot showing the p-values for the parameters from the table ranked from most significant "
                    "to least significant.  Red indicates "
                    "that the p-value is significant, gray indicates that the p-value "
                    "is not significant."
                )
            },
            {
                "id": self.ids("coefficient-plot"),
                "content": (
                    "A plot showing the coefficient values sorted from most to least significant. "
                    "The color scale ranks the coefficients from great positive to great negative. "
                    "The arrows pointing upwards respresent positive coefficients and the arrows pointing "
                    "downwards respesent negative coefficients."
                )
            },
            {"id": self.ids("parameter-list"), "content": ("Choose parameters to consider in the regression."),},
            {"id": self.ids("ensemble"), "content": ("Select the active ensemble."),},
            {"id": self.ids("responses"), "content": ("Select the active response."),},
            {"id": self.ids("max-params"), "content": ("Select the maximum number of parameters to be included in the regression."),},
            {"id": self.ids("force-out"), "content": ("Choose parameters to exclude in the regression."),},
            {"id": self.ids("force-in"), "content": ("Choose parameters to include in the regression."),},
            {"id": self.ids("interaction"), "content": ("Toggle interaction on/off between the parameters."),},
            {"id": self.ids("submit-btn"), "content": ("Click SUBMIT to update the table and the plots."),},
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
                    html.Label("Parameters to be included"),
                    dcc.Dropdown(
                        id=self.ids("parameter-list"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.parameters
                        ],
                        clearable=True,
                        multi=True,
                        value=self.parameters[0:5],
                    ),
                ]
            ),
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
                            {"label": val, "value": val} for val in range(1,min(20,len(self.parameterdf.columns)))
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
                                wcc.Graph(id=self.ids('coefficient-plot')),
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
    def model_input_callbacks(self):
        """List of States for multiple regression callback"""
        callbacks = [
            State(self.ids("parameter-list"), "value"),
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
        """Set callbacks to update dropdown menues"""
        @app.callback(
                Output(self.ids("force-out"), "options"),
            [
                Input(self.ids("parameter-list"), "value"),
                Input(self.ids("force-in"), "value")
            ]
        )
        def update_force_out(parameter_list, force_in=[]):
            """Returns a dictionary with options for force out"""
            fo_lst = list(self.parameterdf[parameter_list].drop(columns=force_in))
            return [{"label": fo, "value": fo} for fo in fo_lst]

        @app.callback(
                Output(self.ids("force-in"), "options"),
            [
                Input(self.ids("parameter-list"), "value"),
                Input(self.ids("force-out"), "value")
            ]
        )
        def update_force_in(parameter_list, force_out=[]):
            """Returns a dictionary with options for force in"""
            fi_lst = list(self.parameterdf[parameter_list].drop(columns=force_out))
            return [{"label": fi, "value": fi} for fi in fi_lst]

        """Set callbacks for the table, p-values plot, and arrow plot"""
        @app.callback(
            [
                Output(self.ids("table"), "data"),
                Output(self.ids("table"), "columns"),
                Output(self.ids("table_title"), "children"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.model_input_callbacks,
        )
        def _update_table(n_clicks, parameter_list, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
            """Callback to update datatable

            1. Filters and aggregates response dataframe per realization
            2. Filters parameters dataframe on selected ensemble
            3. Merge parameter and response dataframe
            4. Fit model using forward stepwise regression, with or without interactions
            5. Generate table
            """
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf[["ENSEMBLE", "REAL"] + parameter_list]
            parameterdf = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            
            #If no selected parameters
            if not parameter_list:
                return(
                        [{"e": ""}],
                        [{"name": "", "id": "e"}],
                        "Please selecet parameters to be included in the model",
                )
            else:
                #Get results and genereate datatable. Gives warning if e.g. divide by zero. Catch this
                with warnings.catch_warnings():
                    warnings.filterwarnings('error', category=RuntimeWarning) #bad? dangerous?
                    warnings.filterwarnings('ignore', category=UserWarning) #bad? dangerous?
                    try:
                        result = gen_model(df, response, force_in = force_in, max_vars = max_vars, interaction= interaction)
                        table = result.model.fit().summary2().tables[1].drop("Intercept")
                        table.drop(["Std.Err.", "t", "[0.025","0.975]"], axis=1, inplace=True)
                        table.index.name = "Parameter"
                        table.reset_index(inplace=True)
                
                        columns = [{"name": i, "id": i, 'type': 'numeric', "format": Format(precision=4)} for i in table.columns]
                        data = table.to_dict("rows")
                        return(
                            data,
                            columns,
                            f"Multiple regression with {response} as response",
                        )
                    except (Exception, RuntimeWarning) as e:
                        #print("error: ", e)
                        return(
                            [{"e": ""}],
                            [{"name": "", "id": "e"}],
                            "Cannot calculate fit for given selection. Select a different response or filter setting",
                        )

        @app.callback(
            [
                Output(self.ids("p-values-plot"), "figure"),
                Output(self.ids("initial-parameter"), "data"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.model_input_callbacks
        )
        def update_pvalues_plot(n_clicks, parameter_list, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
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
            parameterdf = self.parameterdf[["ENSEMBLE", "REAL"] + parameter_list]
            parameterdf = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            
            #Get results and generate p-values plot
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            
             #If no selected parameters
            if not parameter_list:
                return(
                    {
                        "layout": {
                            "title": "<b>Please selecet parameters to be included in the model</b><br>"
                        }
                    },
                    None,
                )
            else:
                #Get results and pvalue-plot. Gives warning if e.g. divide by zero. Catch this
                with warnings.catch_warnings():
                    warnings.filterwarnings('error', category=RuntimeWarning) #bad? dangerous?
                    try:
                        result = gen_model(df, response, force_in = force_in, max_vars = max_vars, interaction = interaction)
                        p_sorted = result.pvalues.sort_values().drop("Intercept")
                        return make_p_values_plot(p_sorted, self.plotly_theme), p_sorted.index[-1]
                    except (Exception, RuntimeWarning) as e:
                        #print("error: ", e)
                        return(
                        {
                            "layout": {
                                "title": "<b>Cannot calculate fit for given selection</b><br>"
                                "Select a different response or filter setting."
                            }
                        },
                        None,
                        )


            
        
        @app.callback(
            [
                Output(self.ids("coefficient-plot"), "figure"),
            ],
            [
                Input(self.ids("submit-btn"), "n_clicks")
            ],
            self.model_input_callbacks
        )
        def update_coefficient_plot(n_clicks, parameter_list, ensemble, response, force_out, force_in, interaction, max_vars, *filters):
            """Callback to update the coefficient plot"""
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf[["ENSEMBLE", "REAL"] + parameter_list]
            parameterdf = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            parameterdf.drop(columns=force_out, inplace=True)

            #For now, remove ':' and ',' form param and response names. Should only do this once though 
            parameterdf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in parameterdf.columns]
            responsedf.columns = [colname.replace(":", "_") if ":" in colname else colname for colname in responsedf.columns]
            responsedf.columns = [colname.replace(",", "_") if "," in colname else colname for colname in responsedf.columns]
            response = response.replace(":", "_")
            response = response.replace(",", "_")
            
            #Get results and generate coefficient plot
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            
             #If no selected parameters
            if not parameter_list:
                return(
                    {
                        "layout": {
                            "title": "<b>Please selecet parameters to be included in the model</b><br>"
                        }
                    },
                )
            else:                
                #Get results and arrow-plot. Gives warning if e.g. divide by zero. Catch this
                with warnings.catch_warnings():
                    warnings.filterwarnings('error', category=RuntimeWarning) #bad? dangerous?
                    try:
                        result = gen_model(df, response, force_in=force_in, max_vars=max_vars, interaction=interaction)
                        #print(make_arrow_plot(result, self.plotly_theme))
                        return make_arrow_plot(result, self.plotly_theme)
                    except (Exception, RuntimeWarning) as e:
                        #print("error: ", e)
                        return(
                            {
                                "layout": {
                                    "title": "<b>Cannot calculate fit for given selection</b><br>"
                                    "Select a different response or filter setting."
                                }
                            },
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



#@CACHE.memoize(timeout=CACHE.TIMEOUT)
def gen_model(
        df: pd.DataFrame,
        response: str,
        max_vars: int=9,
        force_in: list=[],
        interaction: bool=False
    ):
    if interaction:
        df = gen_interaction_df(df,response)
        model = forward_selected(data=df, response=response,force_in=force_in, maxvars=max_vars)
        
    else:
        model = forward_selected(data=df, response=response,force_in=force_in, maxvars=max_vars) 
    return model


def gen_interaction_df(
    df: pd.DataFrame,
    response: str,
    degree: int=2,
    inter_only: bool=True,
    bias: bool=False):

    x_interaction = PolynomialFeatures(
        degree=2,
        interaction_only=inter_only,
        include_bias=False).fit_transform(df.drop(columns=response))

    interaction_df = pd.DataFrame(
        x_interaction,
        columns=gen_column_names(df=df.drop(columns=response)))
    return interaction_df.join(df[response])


def forward_selected(data: pd.DataFrame,
                     response: str, 
                     force_in: list=[], 
                     maxvars: int=5):
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
            if "*" in candidate: # fiks at vi ikke legger til candidate split hvis den allerede er med
                current_model = selected.copy() + [candidate] + list(set(candidate.split("*")).difference(set(selected)))
            else:
                current_model = selected.copy()+[candidate] 
            X = data.filter(items=current_model).to_numpy(dtype="float32")
            p = X.shape[1]
            if n-p-1<1: 
                formula = "{} ~ {} + 1".format(response,
                                   ' + '.join(selected))
                model = smf.ols(formula, data).fit()
                return model
            X = np.append(X, onevec, axis=1)
            try: 
                beta = la.inv(X.T @ X) @ X.T @ y 
            except la.LinAlgError:
                continue
            f_vec = beta @ X.T
            
            
            SS_RES = np.sum((f_vec-y_mean) ** 2)
            r2 = 1-SS_RES/SST
            
            R_2_adj = 1-(1 - (SS_RES / SST))*((n-1)/(n-p-1))
            scores_with_candidates.append((R_2_adj, candidate))
        scores_with_candidates.sort()
        best_new_score, best_candidate = scores_with_candidates.pop()
        if current_score < best_new_score:
            if "*" in best_candidate:
                for base_feature in best_candidate.split("*"):
                    if base_feature in remaining:
                        remaining.remove(base_feature)
                    if base_feature not in selected:
                        selected.append(base_feature)
            
            remaining.remove(best_candidate)
            selected.append(best_candidate)
            current_score = best_new_score
    formula = "{} ~ {} + 1".format(response,
                                   ' + '.join(selected))
    model = smf.ols(formula, data).fit()
    
    return model



def gen_column_names(df: pd.DataFrame, response: str=None):
    if response:
        combine = ["*".join(combination) for combination in combinations(df.drop(columns=response).columns, 2)]
        originals = list(df.drop(columns=response).columns)
        return originals + combine + [response]
    else:
        combine = ["*".join(combination) for combination in combinations(df,2)]
        originals = list(df.columns)
    return originals + combine 



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

def make_arrow_plot(result, theme):
    """Sorting dictionary in descending order. 
    Saving parameters and values of coefficients in lists.
    Saving plot-function to variable fig."""
    param_to_pval = result.pvalues.sort_values().drop("Intercept") #parameters to p-values

    coefs = dict(sorted(result.params.sort_values().drop("Intercept").items(), 
                        key=lambda x: x[1], reverse=True))
    params = list(coefs.keys())
    vals = list(coefs.values())
    sgn = signs(vals)

    param_to_color = param_color_dict(vals, params, sgn) #dictionary with parameters to colors
    fig = arrow_plot(sgn, param_to_pval, param_to_color, theme)

    return [fig] # Need hard brackets here

def signs(vals):
    """Saving signs of coefficients to array sgn"""
    return np.sign(vals)

def arrow_plot(sgn, param_to_pval, param_to_color, theme):
    """Making arrow plot to illutrate relative importance 
    of coefficients to a userdefined response"""
    if len(param_to_pval.index) < 2:
        raise ValueError("Number of coefficients must be greater than 1")
    steps = 2/(len(param_to_pval.index)-1)
    points = len(param_to_pval.index)

    x = np.linspace(0, 2, points)
    y = np.zeros(len(x))

    color_scale=[(0.0, 'rgb(36, 55, 70)'),
                (0.125, 'rgb(102, 115, 125)'),
                (0.25, 'rgb(145, 155, 162)'),
                (0.375, 'rgb(189, 195, 199)'),
                (0.5, 'rgb(255, 231, 214)'),
                (0.625, 'rgb(216, 178, 189)'),
                (0.75, 'rgb(190, 128, 145)'),
                (0.875, 'rgb(164, 76, 101)'),
                (1.0, 'rgb(125, 0, 35)')
                ]

    fig = px.scatter(x=x, y=y, opacity=0, color=sgn, 
                     color_continuous_scale=color_scale,
                     range_color=[-1, 1])
    
    fig.update_layout(
        yaxis=dict(range=[-0.15, 0.15], title='', 
                   showticklabels=False), 
        xaxis=dict(range=[-0.23, x[-1]+0.23], 
                   title='', 
                   ticktext=[p for p in param_to_pval.index], 
                   tickvals=[steps*i for i in range(points)]),
        coloraxis_colorbar=dict(
            title="",
            tickvals=[-0.91, 1],
            ticktext=["Great negative<br>coefficient", 
                      "Great positive<br>coefficient"],
            lenmode="pixels", len=300,
            x=1.1,
        ),
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
                "title": "Sign of coefficients for "
                         "the parameters from the table"
            }
        )
    )
    fig["layout"]["font"].update({"size": 12})

    """Costumizing the hoverer"""
    fig.update_traces(hovertemplate='%{x}') #x is ticktext

    """Adding arrows to figure"""
    for i, s in enumerate(sgn):
        fig.add_shape(
            type="path",
            path=f" M {x[i]-0.025} 0 " \
                    f" L {x[i]-0.025} {s*0.06} " \
                    f" L {x[i]-0.07} {s*0.06} " \
                    f" L {x[i]} {s*0.08} " \
                    f" L {x[i]+0.07} {s*0.06} " \
                    f" L {x[i]+0.025} {s*0.06} " \
                    f" L {x[i]+0.025} 0 ",
            line_color="#222A2A",
            fillcolor=list( map( param_to_color.get, [param_to_pval.index[i]] ) )[0],
            line_width=0.6  
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

    return fig # Should not have hard brackets here

def param_color_dict(vals, params, sgn):
    """Function to scale coefficients to a dark 
    magenta - beige - dusy navy color range"""
    max_val = vals[0]
    min_val = vals[-1]

    standard = 250

    """Defining color values to match theme because I'm 
    lacking knowledge on how to live life with ease"""
    # Initial RGB value
    ri = 125
    gi = 0
    bi = 35

    # Max RGB values
    r0 = 255
    g0 = 231
    b0 = 214

    # Final RGB values
    rf = 36
    gf = 55
    bf = 70

    color_arr = ['']*len(params) #Type: 'rgba(R, G, B, 1)'
    k = 0
    """Adding colors matching scaled values of coefficients to color_arr array"""
    for s, v in zip(sgn, vals):
        if s == 1:
            scaled_val_max = v/max_val
            color_arr[k] = f'rgba({int(ri*(scaled_val_max)+r0*(1-scaled_val_max))}, ' \
                                f'{int(gi*(scaled_val_max)+g0*(1-scaled_val_max))}, ' \
                                f'{int(bi*(scaled_val_max)+b0*(1-scaled_val_max))}, 1)'
        else:
            scaled_val_min = v/min_val
            color_arr[k] = f'rgba({int(r0*(1-scaled_val_min)+rf*(scaled_val_min))}, ' \
                                f'{int(g0*(1-scaled_val_min)+gf*(scaled_val_min))}, ' \
                                f'{int(b0*(1-scaled_val_min)+bf*(scaled_val_min))}, 1)'
        k += 1

    """ USIKKER PÅ HVILKEN for-løkke SOM ER MEST LESEVENNLIG
    for s, v in zip(sgn, vals):
        if s == 1:
            (r, b, g, scaled_val) = (ri, bi, gi, v/max_val)
        else:
            (r, b, g, scaled_val) = (rf, bf, gf, v/min_val)
        
        color_arr[k] = f'rgba({int(r*(scaled_val)+r0*(1-scaled_val))}, ' \
                            f'{int(g*(scaled_val)+g0*(1-scaled_val))}, ' \
                            f'{int(b*(scaled_val)+b0*(1-scaled_val))}, 1)'
        k += 1
    """
    return dict(zip(params, color_arr))

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
