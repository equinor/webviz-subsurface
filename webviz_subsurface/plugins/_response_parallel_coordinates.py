from pathlib import Path

import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.fmu_input import load_parameters, load_csv
from .._utils.ensemble_handling import filter_and_sum_responses


class ResponseParallelCoordinates(WebvizPluginABC):
    """### Best fit using forward stepwise regression

This plugin visualizes parameters used for individual realizations in FMU ensembles.
the parameters can be filtered based on the value of a response.

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
                "Incorrent argument. either provide 'response_include', "
                "'response_ignore' or neither"
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    "Incorrect arguments. Either provide 'csv files' or "
                    "'ensembles and response_file'."
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
                "Incorrect arguments.\
                 Either provide 'csv files' or 'ensembles and response_file'."
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
                    "Dashboard for paralell parameters plot"
                    "filtered to indicate the value of the selected response"
                    
                )
            },
            
            {
                "id": self.uuid("paralell-coords-plot"),
                "content": (
                    "A plot showing the values of all the selected parameter at once."
                    "it is possible to mark a range on each parameters to only show the ones within"
                    "that range, most interesting being the response column to the far right"
                )
            },
            
            {"id": self.uuid("ensemble"), "content": ("Select the active ensemble."), },
            {"id": self.uuid("responses"), "content": ("Select the active response."), },
            {"id": self.uuid("exclude_include"), "content": (
                "choose if the parameter selector should be inclusive or exclusive"
                )
            },
            
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
        """Check that provided response filters are valid"""
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
                   html.Div("Parameters:", style={
                       "font-weight": "bold",
                       "display": "inline-block", 
                        "margin-right": "10px"}),
                   html.Span(
                       "\u003f\u20dd", 
                       id=self.uuid("tooltip-parameters"), 
                       style={
                           "font-weight": "bold",
                           "cursor": "pointer",
                           "fontSize": ".90em",
                           "color": "grey"}),
                   dbc.Tooltip(
                        "This lets you control what parameters to include in your model. \n" +
                        "There are two modes, exclusive and subset: \n" +
                        "- Exclusive mode lets you remove specific parameters\n\n" +
                        "- Subset mode lets you pick a subset of parameters \n",
                    target=self.uuid("tooltip-parameters"),
                    style={"fontSize": ".75em",
                    "backgroundColor": "#505050",
                    "color": "white",
                    "opacity": "85%",
                    "white-space": "pre-wrap"}
                   ),
                   dcc.RadioItems(
                       id=self.uuid("exclude_include"),
                       options=[
                           {"label": "Exclusive mode", "value": "exc"},
                           {"label": "Subset mode", "value": "inc"}
                       ],
                       value="exc",
                       labelStyle={"display": "inline-block"},
                       style={"fontSize": ".80em"},
                   )
               ]
            ),
            html.Div(
                [
                    wcc.Select(
                        id=self.uuid("parameter-list"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.parameters
                        ],
                        multi=True,
                        size=10,
                        value=[],
                        style={"marginBottom": "20px"}
                    ),
                ]
            ),
            html.Div("threshold percentage", style={
                "font-weight": "bold",
                "display": "inline-block",
                "margin-right": "10px"}),
            html.Span(
                       "\u003f\u20dd", 
                       id=self.uuid("tooltip-percent"),
                       style={
                           "font-weight": "bold",
                           "cursor": "pointer",
                           "fontSize": ".90em",
                           "color": "grey"}),
                    dbc.Tooltip(
                        "This lets you control the percenile to be considered 'high'  \n" +
                        "A value is considered low when in the complimentary lower percentile. ",
                    target=self.uuid("tooltip-percent"),
                    style={
                        "fontSize": ".75em",
                        "backgroundColor": "#505050",
                        "color": "white",
                        "opacity": "85%",
                        "white-space": "pre-wrap"}
                   ),
            html.Div(dcc.Slider(
                id=self.uuid("percent"),
                min=50, max=100,
                step=1, value=70,
                marks={x: x for x in range(50, 101, 5)}
                )
            ),
            html.Div("Filters:", style={"font-weight": "bold"}),
            html.Div(children=self.filter_layout),]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=self.control_layout
                ),
                html.Div(
                    style={"flex": 3},
                    children=wcc.Graph(id=self.uuid("paralell-coords-plot")),
                ),
            ]
        )

    @property
    def parallel_coords_callback_Inputs(self):
        """List of Inputs for multiple regression callback"""
        Inputs = [
            Input(self.uuid("exclude_include"), "value"),
            Input(self.uuid("parameter-list"), "value"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("responses"), "value"),
            Input(self.uuid("percent"), "value")

        ]
        if self.response_filters:
            for col_name in self.response_filters:
                Inputs.append(Input(self.uuid(f"filter-{col_name}"), "value"))
        return Inputs

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


        """Set callbacks for the table, p-values plot, and arrow plot"""
        @app.callback(
            Output(self.uuid("paralell-coords-plot"), "figure"),
            self.parallel_coords_callback_Inputs
        )
        def _update_paralell_coordinate_plot(
                exc_inc, parameter_list,
                ensemble, response,
                percent, *filters):
            """Callback to update the model for multiple regression

            1. Filters and aggregates response dataframe per realization.
            2. Filters parameters dataframe on selected ensemble.
            3. Merge parameter and response dataframe.
            4. Discretisize response.
            5. generate parallel parameters plot.
            """
            filteroptions = self.make_response_filters(filters)
            responsedf = filter_and_sum_responses(
                self.responsedf,
                ensemble, response,
                filteroptions=filteroptions,
                aggregation=self.aggregation,
            )
            if exc_inc == "exc":
                parameterdf = self.parameterdf.drop(parameter_list, axis=1)
            elif exc_inc == "inc":
                parameterdf = self.parameterdf[["ENSEMBLE", "REAL"] + parameter_list]
            
            pallete=self.plotly_theme["layout"]["colorway"]
            colmap=((0, pallete[0]), (0.33, pallete[0]), (0.33, pallete[1]), (0.66, pallete[1]), (0.66, pallete[2]), (1, pallete[2]))
            print(colmap)
            
            parameterdf = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"]).drop(columns=["REAL", "ENSEMBLE"])
            df = col_percentile(df, response, percent)
            dims = [{"label": param, "values": df[param]} for param in df]
            data = [{
                "type": "parcoords",
                    "line": {
                        "color": df[response].tolist(),
                        "colorscale": colmap,
                        "showscale": True,
                        "cmin": 1,
                        "cmax": 3,
                        "colorbar": {
                            "title": response,
                            "xanchor": "left",
                            "x": -0.08,
                            "tickvals": [1.3, 2, 2.7],
                            "ticktext": ["low", "medium", "high"],
                            
                        },
                    },
                    "dimensions": dims,
                    "labelangle": 45,
                    "labelside": "bottom",}]
            layout = {}
            layout.update(self.plotly_theme["layout"])
            # Ensure sufficient spacing between each dimension and margin for labels
            width = len(dims) * 100 + 250
            layout.update({"width": width, "height": 1200, "margin": {"b": 740, "t": 30}})
            return {"data": data, "layout": layout}
            
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


def col_percentile(df: pd.DataFrame, column: str, percentile: int):
    col = df[column].sort_values()
    bottom_index = int((100 - percentile) * len(col) / 100)
    top_index = int(percentile * len(col) / 100)
    col[top_index:] = 3
    col[:bottom_index] = 1
    col[bottom_index:top_index] = 2
    df[column] = col.astype("int64")
    return df


def theme_layout(theme, specific_layout):
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout

@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)