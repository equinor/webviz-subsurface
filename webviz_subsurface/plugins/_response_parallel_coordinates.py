from pathlib import Path
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
from .._datainput.fmu_input import load_parameters, load_csv, load_smry
from .._utils.response_aggregation import filter_and_sum_responses


class ResponseParallelCoordinates(WebvizPluginABC):

    """
    Visualizes parameters in a parallel parameter plot, colored by the value of the response.
    Helpful for seeing trends in the relation of the parameters and the response.
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
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading \
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
folder, to avoid risk of not extracting the right data."""

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
            self.parameterdf = read_csv(self.parameter_csv)
            self.responsedf = read_csv(self.response_csv)

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
                'Incorrect arguments. Either provide "csv files" or "ensembles and response_file".'
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
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    @property
    def tour_steps(self):
        steps = [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard for parallel parameters plot"
                    "colored by the value of a response"
                ),
            },
            {
                "id": self.uuid("parameters"),
                "content": (
                    "Lets you control what parameters to include in your plot. \n"
                    + "There are two modes, exclusive and subset: \n"
                    + "- Exclusive mode lets you remove specific parameters\n\n"
                    + "- Subset mode lets you pick a subset of parameters \n"
                ),
            },
            {
                "id": self.uuid("parallel-coords-plot"),
                "content": ("Plot showing the values of all the selected parameters at once."),
            },
            {"id": self.uuid("ensemble"), "content": ("Select the active ensemble."),},
            {"id": self.uuid("responses"), "content": ("Select the active response."),},
            {
                "id": self.uuid("exclude_include"),
                "content": ("Choose if the parameter selector should be inclusive or exclusive"),
            },
        ]
        return steps

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
                    raise ValueError(f"Filter type {col_type} for {col_name} is not valid.")

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
                        id=self.uuid("parameters"),
                        style={
                            "font-weight": "bold",
                            "display": "inline-block",
                            "margin-right": "10px",
                        },
                    ),
                    dcc.RadioItems(
                        id=self.uuid("exclude_include"),
                        options=[
                            {"label": "Exclusive mode", "value": "exc"},
                            {"label": "Subset mode", "value": "inc"},
                        ],
                        value="exc",
                        labelStyle={"display": "inline-block"},
                        style={"fontSize": ".80em"},
                    ),
                ]
            ),
            html.Div(
                [
                    wcc.Select(
                        id=self.uuid("parameter-list"),
                        options=[{"label": ens, "value": ens} for ens in self.parameters],
                        multi=True,
                        size=10,
                        value=[],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            html.Div("Filters:", style={"font-weight": "bold"}),
            html.Div(children=self.filter_layout),
        ]

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(style={"flex": 1}, children=self.control_layout),
                html.Div(
                    style={"flex": 3}, children=wcc.Graph(id=self.uuid("parallel-coords-plot")),
                ),
            ],
        )

    @property
    def parallel_coords_callback_inputs(self):
        """List of Inputs for parallel parameters callback"""
        inputs = [
            Input(self.uuid("exclude_include"), "value"),
            Input(self.uuid("parameter-list"), "value"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("responses"), "value"),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                inputs.append(Input(self.uuid(f"filter-{col_name}"), "value"))
        return inputs

    def make_response_filters(self, filters):
        """Returns a list of active response filters"""
        filteroptions = []
        if filters:
            for i, (col_name, col_type) in enumerate(self.response_filters.items()):
                filteroptions.append({"name": col_name, "type": col_type, "values": filters[i]})
        return filteroptions

    def set_callbacks(self, app):

        """Set callback for parallel coordinates plot"""

        @app.callback(
            Output(self.uuid("parallel-coords-plot"), "figure"),
            self.parallel_coords_callback_inputs,
        )
        def _update_parallel_coordinate_plot(exc_inc, parameter_list, ensemble, response, *filters):
            """
            Callback to update the parallel coordinates plot
            1. Filter Dataframes according to chosen filter options
            5. Generate updated parallel parameters plot.
            """

            # filtering
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

            # plot generation
            pallete = self.plotly_theme["layout"]["colorway"]
            colmap = [(0, pallete[0]), (1, pallete[2])]
            dims = [{"label": param, "values": df[param]} for param in df]
            data = [
                {
                    "type": "parcoords",
                    "line": {
                        "color": df[response],
                        "colorscale": colmap,
                        "showscale": True,
                        "colorbar": {"title": response, "xanchor": "right", "x": -0.02,},
                    },
                    "dimensions": dims,
                    "labelangle": 45,
                    "labelside": "bottom",
                }
            ]
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
            ),
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)
