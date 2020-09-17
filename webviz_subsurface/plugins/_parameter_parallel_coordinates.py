from pathlib import Path

import pandas as pd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._datainput.fmu_input import load_parameters, load_csv, load_smry
from .._utils.parameter_response import filter_and_sum_responses


class ParameterParallelCoordinates(WebvizPluginABC):
    """Visualizes parameters used in FMU ensembles side-by-side. Also supports response coloring.

Useful to investigate:
* Initial parameter distributions, and convergence of parameters over multiple iterations.
* Trends in relations between parameters and responses.

!> At least two parameters have to be selected to make the plot work.

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
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` \
                implies that the input data should be time series data from simulation `.UNSMRY` \
                files, read using `fmu-ensemble`.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading \
                from UNSMRY-files in the defined ensembles (default is all vectors). * can be \
                used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from \
               `.UNSMRY`-files (default is monthly).
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter \
   of type `single` (as defined below under `response_filters`).

**Using the plugin without responses**
It is possible to use the plugin with only parameter data, in that case set the option \
`no_responses` to True, and give either `ensembles` or `parameter_csv` as input as described \
above. Response coloring and filtering will then not be available.

**Common settings for responses**
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

Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

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

    # pylint: disable=too-many-arguments,too-many-branches
    def __init__(
        self,
        app,
        ensembles: list = None,
        parameter_csv: Path = None,
        response_csv: Path = None,
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        parameter_ignore: list = None,
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
        no_responses=False,
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
        self.no_responses = no_responses

        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. Either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "parameter_csv" or '
                    '"ensembles and/or response_file".'
                )
            if not self.no_responses:
                if self.response_csv:
                    self.responsedf = read_csv(self.response_csv)
                else:
                    raise ValueError("Incorrect arguments. Missing response_csv.")
            self.parameterdf = read_csv(self.parameter_csv)

        elif ensembles:
            if self.response_csv:
                raise ValueError(
                    'Incorrect arguments. Either provide "response_csv" or '
                    '"ensembles and/or response_file".'
                )
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.parameterdf = load_parameters(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
            if not self.no_responses:
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
                "Incorrect arguments."
                'You have to define at least "ensembles" or "parameter_csv".'
            )
        if not self.no_responses:
            self.check_runs()
            self.check_response_filters()
            if response_ignore:
                self.responsedf.drop(
                    response_ignore, errors="ignore", axis=1, inplace=True
                )
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

        # Integer value for each ensemble to be used for ensemble colormap
        # self.uuid("COLOR") used to mitigate risk of already having a column named "COLOR" in the
        # DataFrame.
        self.parameterdf[self.uuid("COLOR")] = self.parameterdf.apply(
            lambda row: self.ensembles.index(row["ENSEMBLE"]), axis=1
        )

        self.theme = app.webviz_settings["theme"]
        self.set_callbacks(app)

    @property
    def parameters(self):
        """Returns numerical input parameters"""
        return list(
            self.parameterdf.drop(["ENSEMBLE", "REAL", self.uuid("COLOR")], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )

    @property
    def responses(self):
        """Returns valid responses. Filters out non numerical columns,
        and filterable columns."""
        responses = list(
            self.responsedf.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )
        return [p for p in responses if p not in self.response_filters.keys()]

    @property
    def ensembles(self):
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def ens_colormap(self):
        """Returns a discrete colormap with one color per ensemble"""
        colors = self.theme.plotly_theme["layout"]["colorway"]
        colormap = []
        for i in range(0, len(self.ensembles)):
            colormap.append([i / len(self.ensembles), colors[i]])
            colormap.append([(i + 1) / len(self.ensembles), colors[i]])

        return colormap

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

    def make_response_filters(self, filters):
        """Returns a list of active response filters"""
        filteroptions = []
        if filters:
            for i, (col_name, col_type) in enumerate(self.response_filters.items()):
                filteroptions.append(
                    {"name": col_name, "type": col_type, "values": filters[i]}
                )
        return filteroptions

    @property
    def response_layout(self):
        """Layout to display selectors for response filters"""

        if self.no_responses:
            return []
        children = [
            html.Span("Response:", style={"font-weight": "bold"}),
            dcc.Dropdown(
                id=self.uuid("responses"),
                options=[{"label": ens, "value": ens} for ens in self.responses],
                clearable=False,
                value=self.responses[0],
                style={"marginBottom": "20px"},
                persistence=True,
                persistence_type="session",
            ),
        ]

        if self.response_filters is not None:
            for col_name, col_type in self.response_filters.items():
                values = list(self.responsedf[col_name].unique())
                if col_type == "multi":
                    selector = wcc.Select(
                        id=self.uuid(f"filter-{col_name}"),
                        options=[{"label": val, "value": val} for val in values],
                        value=values,
                        multi=True,
                        size=min(20, len(values)),
                        persistence=True,
                        persistence_type="session",
                    )
                elif col_type == "single":
                    selector = dcc.Dropdown(
                        id=self.uuid(f"filter-{col_name}"),
                        options=[{"label": val, "value": val} for val in values],
                        value=values[0],
                        multi=False,
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                    )
                children.append(
                    html.Div(
                        children=[
                            html.Label(col_name),
                            selector,
                        ]
                    )
                )
        return [
            html.Div(
                id=self.uuid("view_response"),
                style={"display": "none"},
                children=children,
            ),
        ]

    @property
    def control_layout(self):
        """Layout to select ensembles and parameters"""
        mode_select = (
            []
            if self.no_responses
            else [
                html.Label(
                    children=[
                        html.Span("Mode:", style={"font-weight": "bold"}),
                        dcc.RadioItems(
                            id=self.uuid("mode"),
                            options=[
                                {"label": "Ensemble", "value": "ensemble"},
                                {"label": "Response", "value": "response"},
                            ],
                            value="ensemble",
                            labelStyle={"display": "inline-block"},
                            persistence=True,
                            persistence_type="session",
                        ),
                    ]
                )
            ]
        )

        return mode_select + [
            html.Span("Ensemble:", style={"font-weight": "bold"}),
            wcc.Select(
                id=self.uuid("ensembles"),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                multi=True,
                value=self.ensembles,
                size=min(len(self.ensembles), 10),
                persistence=True,
                persistence_type="session",
            ),
            html.Label(
                children=[
                    html.Span(
                        "Parameters:",
                        id=self.uuid("parameters"),
                        style={
                            "font-weight": "bold",
                        },
                    ),
                    dcc.RadioItems(
                        id=self.uuid("exclude_include"),
                        options=[
                            {"label": "Exclude", "value": "exc"},
                            {"label": "Include", "value": "inc"},
                        ],
                        value="exc",
                        labelStyle={"display": "inline-block"},
                        style={"fontSize": ".80em"},
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
            wcc.Select(
                id=self.uuid("parameter-list"),
                options=[{"label": ens, "value": ens} for ens in self.parameters],
                multi=True,
                size=min(len(self.parameters), 15),
                value=[],
                style={
                    "marginBottom": "20px",
                    "fontSize": ".80em",
                    "overflowX": "auto",
                },
                persistence=True,
                persistence_type="session",
            ),
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=(self.control_layout + self.response_layout),
                ),
                html.Div(
                    style={"flex": 3},
                    children=wcc.Graph(
                        id=self.uuid("parcoords"),
                    ),
                ),
            ],
        )

    @property
    def parcoord_inputs(self):
        inputs = [
            Input(self.uuid("ensembles"), "value"),
            Input(self.uuid("exclude_include"), "value"),
            Input(self.uuid("parameter-list"), "value"),
        ]
        if not self.no_responses:
            inputs.extend(
                [
                    Input(self.uuid("mode"), "value"),
                    Input(self.uuid("responses"), "value"),
                ]
            )
            if self.response_filters is not None:
                inputs.extend(
                    [
                        Input(self.uuid(f"filter-{col}"), "value")
                        for col in self.response_filters
                    ]
                )
        return inputs

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("parcoords"), "figure"),
            self.parcoord_inputs,
        )
        def _update_parcoord(ens, exc_inc, parameter_list, *opt_args):
            """Updates parallel coordinates plot
            Filter dataframe for chosen ensembles and parameters
            Call render_parcoord to render new figure
            """
            # Ensure selected ensembles is a list
            ens = ens if isinstance(ens, list) else [ens]
            # Ensure selected parameters is a list
            parameter_list = (
                parameter_list if isinstance(parameter_list, list) else [parameter_list]
            )
            special_columns = ["ENSEMBLE", "REAL", self.uuid("COLOR")]
            if exc_inc == "exc":
                parameterdf = self.parameterdf.drop(parameter_list, axis=1)
            elif exc_inc == "inc":
                parameterdf = self.parameterdf[special_columns + parameter_list]
            params = [
                param
                for param in parameterdf.columns
                if param not in special_columns and param in self.parameters
            ]

            mode = opt_args[0] if opt_args else "ensemble"
            # Need a default response
            response = ""

            if mode == "response":
                if len(ens) != 1:
                    # Need to wait for update of ensemble selector to multi=False
                    raise PreventUpdate
                df = parameterdf.loc[self.parameterdf["ENSEMBLE"] == ens[0]]
                response = opt_args[1]
                response_filters = opt_args[2:] if len(opt_args) > 2 else {}
                filteroptions = self.make_response_filters(response_filters)
                responsedf = filter_and_sum_responses(
                    self.responsedf,
                    ens[0],
                    response,
                    filteroptions=filteroptions,
                    aggregation=self.aggregation,
                )
                # Renaming to make it clear in plot.
                responsedf.rename(
                    columns={response: f"Response: {response}"}, inplace=True
                )
                df = pd.merge(responsedf, df, on=["REAL"]).drop(columns=special_columns)
            else:
                # Filter on ensembles (ens) and active parameters (params),
                # adding the COLOR column to the columns to keep
                df = self.parameterdf[self.parameterdf["ENSEMBLE"].isin(ens)][
                    params + [self.uuid("COLOR")]
                ]
            return render_parcoord(
                df,
                self.theme,
                self.ens_colormap,
                self.uuid("COLOR"),
                self.ensembles,
                mode,
                params,
                response,
            )

        @app.callback(
            [
                Output(self.uuid("ensembles"), "multi"),
                Output(self.uuid("ensembles"), "value"),
                Output(self.uuid("view_response"), "style"),
            ],
            [Input(self.uuid("mode"), "value")],
        )
        def _update_mode(mode: str):
            if mode == "ensemble":
                return True, self.ensembles, {"display": "none"}
            if mode == "response":
                return False, self.ensembles[0], {"display": "block"}
            # The error should never occur
            raise ValueError("ensemble and response are the only valid modes.")

    def add_webvizstore(self):
        functions = []
        if self.parameter_csv:
            functions.append(
                (
                    read_csv,
                    [
                        {
                            "csv_file": self.parameter_csv,
                        }
                    ],
                )
            )
            if self.response_csv:
                functions.append(
                    (
                        read_csv,
                        [
                            {
                                "csv_file": self.response_csv,
                            }
                        ],
                    )
                )
        else:
            functions.append(
                (
                    load_parameters,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                        }
                    ],
                ),
            )
            if not self.no_responses:
                if self.response_file:
                    functions.append(
                        (
                            load_csv,
                            [
                                {
                                    "ensemble_paths": self.ens_paths,
                                    "csv_file": self.response_file,
                                }
                            ],
                        ),
                    )
                else:
                    functions.append(
                        (
                            load_smry,
                            [
                                {
                                    "ensemble_paths": self.ens_paths,
                                    "column_keys": self.column_keys,
                                    "time_index": self.time_index,
                                }
                            ],
                        ),
                    )

        return functions


def render_parcoord(plot_df, theme, colormap, color_col, ens, mode, params, response):
    """Renders parallel coordinates plot"""
    colormap = (
        colormap if mode == "ensemble" else theme.plotly_theme["layout"]["colorway"]
    )
    if response:
        response = f"Response: {response}"
        params = [response] + params
    # Create parcoords dimensions (one per parameter)
    dimensions = [{"label": param, "values": plot_df[param]} for param in params]
    data = [
        {
            "line": {
                "color": plot_df[color_col].values.tolist(),
                "colorscale": colormap,
                "cmin": -0.5,
                "cmax": len(ens) - 0.5,
                "showscale": True,
                "colorbar": {
                    "tickvals": list(range(0, len(ens))),
                    "ticktext": ens,
                    "title": "Ensemble",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.2 * len(ens),
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
            "type": "parcoords",
        }
        if mode == "ensemble"
        else {
            "type": "parcoords",
            "line": {
                "color": plot_df[response],
                "colorscale": colormap,
                "showscale": True,
                "colorbar": {
                    "title": {"text": response},
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
        }
        if mode == "response"
        else {}
    ]

    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 80 + 250
    layout = {"width": width, "height": 1200, "margin": {"b": 740, "t": 30}}
    return {"data": data, "layout": theme.create_themed_layout(layout)}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)
