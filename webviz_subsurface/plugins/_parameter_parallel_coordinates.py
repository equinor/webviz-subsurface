from pathlib import Path

import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface._utils.parameter_response as parresp
from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)


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

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
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
        self.column_keys = column_keys
        self.time_index = sampling
        self.aggregation = aggregation
        self.no_responses = no_responses
        self.response_columns = []

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
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths={
                        ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                        for ens in ensembles
                    },
                    time_index=self.time_index,
                    column_keys=self.column_keys,
                )
            )
            self.parameterdf = self.emodel.load_parameters()
            if not self.no_responses:
                if self.response_file:
                    self.responsedf = self.emodel.load_csv(csv_file=response_file)
                else:
                    self.responsedf = self.emodel.get_or_load_smry_cached()
                    self.response_filters["DATE"] = "single"
        else:
            raise ValueError(
                "Incorrect arguments."
                'You have to define at least "ensembles" or "parameter_csv".'
            )

        if not self.no_responses:
            parresp.check_runs(parameterdf=self.parameterdf, responsedf=self.responsedf)
            parresp.check_response_filters(
                responsedf=self.responsedf, response_filters=self.response_filters
            )
            # only select numerical responses
            self.response_columns = parresp.filter_numerical_columns(
                df=self.responsedf,
                column_ignore=response_ignore,
                column_include=response_include,
                filter_columns=self.response_filters.keys(),
            )

        # Only select numerical parameters
        self.parameter_columns = parresp.filter_numerical_columns(
            df=self.parameterdf, column_ignore=parameter_ignore
        )

        self.theme = webviz_settings.theme
        self.set_callbacks(app)

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

    @property
    def response_layout(self):
        """Layout to display selectors for response filters"""

        if self.no_responses:
            return []
        children = [
            wcc.Dropdown(
                label="Response",
                id=self.uuid("responses"),
                options=[{"label": ens, "value": ens} for ens in self.response_columns],
                clearable=False,
                value=self.response_columns[0],
                style={"marginBottom": "20px"},
            ),
        ]

        if self.response_filters is not None:
            for col_name, col_type in self.response_filters.items():
                values = list(self.responsedf[col_name].unique())
                if col_type == "multi":
                    children.append(
                        wcc.SelectWithLabel(
                            label=col_name,
                            id=self.uuid(f"filter-{col_name}"),
                            options=[{"label": val, "value": val} for val in values],
                            value=values,
                            multi=True,
                            size=min(20, len(values)),
                        )
                    )
                elif col_type == "single":
                    children.append(
                        wcc.Dropdown(
                            label=col_name,
                            id=self.uuid(f"filter-{col_name}"),
                            options=[{"label": val, "value": val} for val in values],
                            value=values[0],
                            multi=False,
                            clearable=False,
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
                wcc.Selectors(
                    label="Mode",
                    children=[
                        wcc.RadioItems(
                            id=self.uuid("mode"),
                            options=[
                                {"label": "Ensemble", "value": "ensemble"},
                                {"label": "Response", "value": "response"},
                            ],
                            value="ensemble",
                        ),
                    ],
                )
            ]
        )

        return mode_select + [
            wcc.Selectors(
                label="Ensembles",
                children=wcc.SelectWithLabel(
                    id=self.uuid("ensembles"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    multi=True,
                    value=self.ensembles,
                    size=min(len(self.ensembles), 10),
                ),
            ),
            wcc.Selectors(
                label="Parameter filter",
                children=[
                    wcc.RadioItems(
                        id=self.uuid("exclude_include"),
                        options=[
                            {"label": "Exclude", "value": "exc"},
                            {"label": "Include", "value": "inc"},
                        ],
                        value="exc",
                    ),
                    wcc.SelectWithLabel(
                        label="Parameters",
                        id=self.uuid("parameter-list"),
                        options=[
                            {"label": ens, "value": ens}
                            for ens in self.parameter_columns
                        ],
                        multi=True,
                        size=min(len(self.parameter_columns), 15),
                        value=[],
                    ),
                ],
            ),
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            style={"height": "90vh"},
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=(self.control_layout + self.response_layout),
                ),
                wcc.Frame(
                    style={"flex": 4, "height": "90vh", "marginRight": "2vw"},
                    color="white",
                    highlight=False,
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
            special_columns = ["ENSEMBLE", "REAL"]
            if exc_inc == "exc":
                parameterdf = self.parameterdf.drop(parameter_list, axis=1)
            elif exc_inc == "inc":
                parameterdf = self.parameterdf[special_columns + parameter_list]
            params = [
                param
                for param in parameterdf.columns
                if param not in special_columns and param in self.parameter_columns
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
                response_filter_values = opt_args[2:] if len(opt_args) > 2 else {}
                filteroptions = parresp.make_response_filters(
                    response_filters=self.response_filters,
                    response_filter_values=response_filter_values,
                )
                responsedf = parresp.filter_and_sum_responses(
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
                df[self.uuid("COLOR")] = df.apply(
                    lambda row: self.ensembles.index(ens[0]), axis=1
                )
            else:
                # Filter on ensembles (ens) and active parameters (params),
                # adding the COLOR column to the columns to keep
                df = self.parameterdf[self.parameterdf["ENSEMBLE"].isin(ens)][
                    params + ["ENSEMBLE"]
                ]
                df[self.uuid("COLOR")] = df.apply(
                    lambda row: self.ensembles.index(row["ENSEMBLE"]), axis=1
                )
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
            functions.extend(self.emodel.webvizstore)

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
