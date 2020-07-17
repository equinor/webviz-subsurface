from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from dash_table import DataTable
from dash.dependencies import Input, Output
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

import plotly.figure_factory as ff

import math

class MultipleRegressionSara(WebvizPluginABC):
    #""" Plugin. Generates arrowplot from multiple regression fit """

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
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme #imported for theme
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
            #elif col_type == "range":
                #selector = make_range_slider(domid, self.responsedf[col_name], col_name)
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
            html.Div(
                [
                    html.Label("Number of variables"),
                    dcc.Dropdown(
                        id=self.ids("max_vars"),
                        options=[
                            {"label": val, "value": val} for val in range(1,min(10,len(self.parameterdf.columns)))
                        ],
                        clearable=False,
                        value=3,
                    ),
                ]
            ),

        ]

    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(style={"flex": 3},
                    children=[
                        html.Div(
                            style={'flex': 3},
                            children=wcc.Graph(id=self.ids('coefficient-plot'))
                        )
                    ],
                ),
                html.Div(
                    style={"flex": 1},
                    children=self.control_layout + self.filter_layout
                    if self.response_filters
                    else [],
                ),
            ]
        )

    @property
    def coefficientplot_input_callbacks(self):
        """List of inputs for coefficient plot callback"""
        callbacks = [
            Input(self.ids("ensemble"), "value"),
            Input(self.ids("responses"), "value"),
            Input(self.ids("interaction"), "value"),
            Input(self.ids("max_vars"), "value"),
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
        """Temporary way of filtering out stupid parameters"""
        parameter_filters=[
                'RMSGLOBPARAMS:FWL', 'MULTFLT:MULTFLT_F1', 'MULTFLT:MULTFLT_F2',
                'MULTFLT:MULTFLT_F3', 'MULTFLT:MULTFLT_F4', 'MULTFLT:MULTFLT_F5', 
                'MULTZ:MULTZ_MIDREEK', 'INTERPOLATE_RELPERM:INTERPOLATE_GO',
                'INTERPOLATE_RELPERM:INTERPOLATE_WO', 'LOG10_MULTFLT:MULTFLT_F1', 
                'LOG10_MULTFLT:MULTFLT_F2', 'LOG10_MULTFLT:MULTFLT_F3',
                'LOG10_MULTFLT:MULTFLT_F4', 'LOG10_MULTFLT:MULTFLT_F5',
                'LOG10_MULTZ:MULTZ_MIDREEK', "RMSGLOBPARAMS:COHIBA_MODEL_MODE",
                "COHIBA_MODEL_MODE"]

        """Set callbacks for the coefficient plot"""
        @app.callback(
            [
                Output(self.ids("coefficient-plot"), "figure")
            ],
            self.coefficientplot_input_callbacks
        )
        def update_coefficient_plot(ensemble, response, interaction, max_vars, *filters):
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
            param_df = parameterdf.drop(columns=parameter_filters)
            
            df = pd.merge(responsedf, param_df, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            model = gen_model(df, response, max_vars = max_vars, interaction= interaction)
            
            return make_arrow_plot(model, self.plotly_theme)

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


def make_arrow_plot(model, theme):
    """Sorting dictionary in descending order. 
    Saving parameters and values of coefficients in lists.
    Saving plot-function to variable fig."""
    coefs = dict(sorted(model.params.sort_values().items(), key=lambda x: x[1], reverse=True))
    params = list(coefs.keys())
    vals = list(coefs.values())
    sgn = signs(vals)
    colors = color_array(vals, params, sgn)

    fig = arrow_plot(coefs, vals, params, sgn, colors, theme)

    return [fig]

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

    global fig
    #fig = px.scatter(x=x, y=y, opacity=0, color=sgn, color_continuous_scale=[theme["layout"]["colorscale"]["sequential"][:][:]], range_color=[-1, 1]) # Rejected because of hard brackets. Modified in the line below. Error: Received value: [[[0.0, 'rgb(36, 55, 70)'], [0.125, 'rgb(102, 115, 125)'], [0.25, 'rgb(145, 155, 162)'], [0.375, 'rgb(189, 195, 199)'], [0.5, 'rgb(255, 231, 214)'], [0.625, 'rgb(216, 178, 189)'], [0.75, 'rgb(190, 128, 145)'], [0.875, 'rgb(164, 76, 101)'], [1.0, 'rgb(125, 0, 35)']]]
    fig = px.scatter(x=x, y=y, opacity=0, color=sgn, color_continuous_scale=[(0.0, 'rgb(36, 55, 70)'), (0.125, 'rgb(102, 115, 125)'), (0.25, 'rgb(145, 155, 162)'), (0.375, 'rgb(189, 195, 199)'), (0.5, 'rgb(255, 231, 214)'), (0.625, 'rgb(216, 178, 189)'), (0.75, 'rgb(190, 128, 145)'), (0.875, 'rgb(164, 76, 101)'), (1.0, 'rgb(125, 0, 35)')], range_color=[-1, 1]) # Theme, replaced [] with () as hard brackets were rejected:(
    fig.update_xaxes(
        ticktext=[p for p in params],
        tickvals=[steps*i for i in range(points)],
    )
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(
        yaxis=dict(range=[-0.125, 0.125], title=f'', showgrid=False), 
        xaxis=dict(range=[-0.2, x[-1]+0.2], title='Parameters', showgrid=False, zeroline=False),
        title='Sign of coefficient of the key parameter combination',
        autosize=False,
        width=725,
        height=500,
        plot_bgcolor='#FFFFFF',
        coloraxis_colorbar=dict(
            title="",
            tickvals=[-0.97, -0.88, 0.88, 0.97],
            ticktext=["coefficient", "Great negative", "coefficient", "Great positive"],
            lenmode="pixels", len=300,
        ),
        hoverlabel=dict(
            bgcolor="white", 
            font_size=12, 
        )
    )

    """Costumizing the hoverer"""
    fig.update_traces(hovertemplate='Parameter: %{x}')

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
    fig.add_shape(
        # Arrowhead, left
        type="path",
        path=" M -0.2 0 L -0.18 -0.005 L -0.18 0.005 Z",
        line_color="#222A2A",
        line_width=0.75,
    )
    fig.add_shape(
        # Arrowhead, right
        type="path",
        path=f" M {x[-1]+0.2} 0 L {x[-1]+0.18} -0.005 L {x[-1]+0.18} 0.005 Z",
        line_color="#222A2A",
        line_width=0.75,
    )

    """Adding arrows to figure"""
    for i, s in enumerate(sgn):
        if s == 1:
            fig.add_shape(
                type="path",
                path=f" M {x[i]} 0 L {x[i]} 0.1 L {x[i]-0.05} 0.075 L {x[i]} 0.1 L {x[i]+0.05} 0.075",
                line_color=colors[i],     
            )
        else:
            fig.add_shape(
                type="path",
                path=f" M {x[i]} 0 L {x[i]} -0.1 L {x[i]-0.05} -0.075 L {x[i]} -0.1 L {x[i]+0.05} -0.075",
                line_color=colors[i],
            )

    return fig

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

    global k
    k=0

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
