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
import statsmodels.formula.api as smf
from sklearn.preprocessing import PolynomialFeatures

from .._datainput.fmu_input import load_parameters, load_csv


class MultipleRegressionJostein(WebvizPluginABC):

        # pylint:disable=too-many-arguments
        # plug-in tar in enten en csv fil eller en ensemble og div filter
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
        parameter_filters: dict = None,
        parameter_ignore: list = None,
        parameter_include: list = None,
        aggregation: str = "sum",
    ):

        super().__init__()
        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.response_ignore = response_ignore if response_ignore else None
        
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
            self.parameterdf = pd.read_csv(self.parameter_csv)
            self.responsedf = pd.read_csv(self.response_csv)
            
# her lager vi parameter og response DataFrames
        elif ensembles and response_file:
            self.ens_paths = {
                ens: app.webviz_settings[
                    "shared_settings"]["scratch_ensembles"][ens]
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
                """Incorrect arguments.
                Either provide "csv files" or "ensembles and response_file"."""
            )

        self.check_runs()
        self.check_response_filters()
        if response_ignore:
            self.responsedf.drop(
                response_ignore,
                errors="ignore",
                axis=1,
                inplace=True)

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
        parameters =[(param.replace(":","_") if ":" in param else param) for param in parameters]
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
                raise ValueError("Parameter and response\
                     files have different runs")

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
            elif col_type == "range":
                selector = make_range_slider(
                    domid,
                    self.responsedf[col_name],
                    col_name)
            else:
                return children
            children.append(html.Div(
                children=[html.Label(col_name),
                          selector, ]))

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
                            {"label": ens,
                             "value": ens} for ens in self.ensembles
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
                            {"label": ens,
                             "value": ens} for ens in self.responses
                        ],
                        clearable=False,
                        value=self.responses[0],
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Interaction"),
                    dcc.RadioItems(
                        id=self.ids("interaction"),
                        options=[
                            {"label": "on", "value": True},
                            {"label": "off", "value": False}
                        ],
                        value=False
                        )
                ]
            ),
            html.Div(
                [
                    html.Label("Force out"),
                    dcc.Dropdown(
                        id=self.ids("force out"),
                        options=[
                            {"label": param,
                             "value": param} for param in self.parameters
                        ],
                        clearable=True,
                        multi=True,
                        value=["FWL", "INTERPOLATE_WO"],
                        
                    )
                ]
            ),
            html.Div(
                [
                    html.Label("number of variables"),
                    dcc.Input(
                        id=self.ids("nvars"),
                        type="number",
                        debounce=True,
                        placeholder="Max variables",
                        min=1,
                        max=len(self.parameterdf),
                        step=1,
                        value=9,
                        
                    )
                ]
            )
        ]

    @property
    def correlation_input_callbacks(self):
        """List of Inputs for correlation callback"""
        callbacks = [
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(
                    Input(self.ids(f"filter-{col_name}"), "value"))
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

    def forward_selected(data, response, maxvars=3):
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
        selected = []

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

    @property
    def model_input_callbacks(self):
        hollabacks = [
            # Input(self.ids("initial-parameter"), "data"),
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"),"value"),
            Input(self.ids("interaction"), "value"),
            Input(self.ids("force out"), "value"),
            Input(self.ids("nvars"), "value")
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                hollabacks.append(Input(self.ids(f"filter-{col_name}"), "value"))
        return hollabacks


    def set_callbacks(self, app):
            @app.callback(
                [
                    Output(self.ids("p-values-graph"), "figure")
                ],
                self.model_input_callbacks,
            )
            def update_pvalue_plot(ensemble, response, interaction, force_out, nvars, *filters):
                filteroptions = self.make_response_filters(filters)
                responsedf = filter_and_sum_responses(
                    self.responsedf,
                    ensemble,
                    response,
                    filteroptions=filteroptions,
                    aggregation=self.aggregation,
                )
                paramdf = self.parameterdf

                paramdf.columns = [colname.replace(":","_") if ":" in colname else colname for colname in paramdf.columns]
                paramdf = paramdf.loc[paramdf["ENSEMBLE"] == ensemble]
                paramdf.drop(columns=force_out, inplace=True)
                
                df = pd.merge(responsedf, paramdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
                model = gen_model(df, response, nvars, interaction)
                return make_p_values_plot(model)


            

    
    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(
                    style={'flex': 2},
                    children=wcc.Graph(
                        id=self.ids('p-values-graph'),
                        figure={
                            "data": [{"type": "bar", "x": [1, 2, 3],"y": [1, 3, 2]}],
                            "layout": {"title": {"text": "A Figure Specified By Python Dictionary"}}
                                }
                    )
                ),
                html.Div(
                    style={"flex": 1},
                    children=self.control_layout + self.filter_layout
                    if self.response_filters
                    else [],
                ),
            ],
        )      

def make_p_values_plot(model):
    """ Sorting the dictionary in ascending order and making lists for parameters and p-values """
    p_sorted = model.pvalues.sort_values()
    parameters = p_sorted.index
    values = p_sorted.values

    """ Making an array for the corresponding colors """
    
    colors = ["#FF1243" if val<0.05 else "slate-gray" for val in values]
    
    dict_fig = dict(
        {"data": [
                {
                    "type": "bar",
                    "x": parameters,
                    "y": values,
                    "marker": {"color": colors}
                }], 
        })
    return [dict_fig]
"""
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def generate_model(ensemble, response, interaction, *filters):

            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            parameterdf = self.parameterdf.loc[
                self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])
            return model(df, response, interaction)
"""
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


def gen_model(
        df: pd.DataFrame,
        response: str,
        max_vars: int=9,
        interaction: bool=False):
        
        if interaction:
            df = gen_interaction_df(df, response)
            return forward_selected_interaction(df, response, maxvars=max_vars)
        else:
            return forward_selected(df, response, maxvars=max_vars)


def gen_interaction_df(
    df: pd.DataFrame,
    response: str,
    degree: int=2,
    inter_only: bool=False,
    bias: bool=False):

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


def forward_selected_interaction(data, response, maxvars=9):
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
    selected = []
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


def forward_selected(data, response, maxvars=9):
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
    selected = []

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

def gen_column_names(df, interaction_only):
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
