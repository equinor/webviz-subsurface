from pathlib import Path
import json

import yaml
import pandas as pd
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from .._datainput.fmu_input import load_smry, load_smry_meta
from .._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
    historical_vector,
)
from .._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
    get_simulation_line_shape,
    calc_series_statistics,
    add_fanchart_traces,
)
from .._utils.unique_theming import unique_colors


class ReservoirSimulationTimeSeries(WebvizPluginABC):
    """Visualizes reservoir simulation time series data for FMU ensembles.

---
**Two main options for input data: Aggregated and read from UNSMRY.**

**Using aggregated data**
* **`csvfile`:** Aggregated csv file with `REAL`, `ENSEMBLE`, \
    `DATE` and vector columns.

**Using simulation time series data directly from `UNSMRY` files**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.

**Common optional settings for both input options**
* **`obsfile`**: File with observations to plot together with the relevant time series. \
(absolute path or relative to config file).
* **`options`:** Options to initialize plots with:
    * `vector1` : First vector to display
    * `vector2` : Second vector to display
    * `vector3` : Third vector to display
    * `visualization` : `realizations`, `statistics` or `statistics_hist`
    * `date` : Date to show in histograms
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as \
    rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are \
    always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

---

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will \
be plotted together with their non-historical counterparts as reference lines, and they are \
therefore not selectable as vectors to plot initially.

?> The `obsfile` is a common (optional) file for all ensembles, which currently has to be made \
manually. [An example of the format can be found here]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/share/observations/observations.yml).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like \
`monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.

**Using aggregated data**

The `csvfile` must have columns `ENSEMBLE`, `REAL` and `DATE` in addition to the individual
vectors.
* [Example of aggregated file]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/smry.csv).

**Using simulation time series data directly from `.UNSMRY` files**

Vectors are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other \
speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.
"""

    ENSEMBLE_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]
    # pylint:disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        obsfile: Path = None,
        column_keys: list = None,
        sampling: str = "monthly",
        options: dict = None,
        line_shape_fallback: str = "linear",
    ):

        super().__init__()

        self.csvfile = csvfile
        self.obsfile = obsfile
        self.time_index = sampling
        self.column_keys = column_keys
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )
        self.observations = {}
        if obsfile:
            with open(get_path(self.obsfile), "r") as stream:
                self.observations = format_observations(
                    yaml.safe_load(stream).get("smry", [dict()])
                )
        if csvfile:
            self.smry = read_csv(csvfile)
            self.smry_meta = None
        elif ensembles:
            self.ens_paths = {
                ensemble: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                    ensemble
                ]
                for ensemble in ensembles
            }
            self.smry = load_smry(
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
                time_index=self.time_index,
                column_keys=self.column_keys,
            )
            self.smry_meta = load_smry_meta(
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
                column_keys=self.column_keys,
            )
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )

        self.smry_cols = [
            c
            for c in self.smry.columns
            if c not in ReservoirSimulationTimeSeries.ENSEMBLE_COLUMNS
            and not historical_vector(c, self.smry_meta, False) in self.smry.columns
        ]

        self.dropdown_options = [
            {"label": f"{simulation_vector_description(vec)} ({vec})", "value": vec}
            for vec in self.smry_cols
        ]

        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.theme = app.webviz_settings["theme"]
        self.plot_options = options if options else {}
        self.plot_options["date"] = (
            str(self.plot_options.get("date"))
            if self.plot_options.get("date")
            else None
        )
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        # Check if initially plotted vectors exist in data, raise ValueError if not.
        missing_vectors = [
            value
            for key, value in self.plot_options.items()
            if key in ["vector1", "vector2", "vector3"] and value not in self.smry_cols
        ]
        if missing_vectors:
            raise ValueError(
                f"Cannot find: {', '.join(missing_vectors)} to plot initially in "
                "ReservoirSimulationTimeSeries. Check that the vectors exist in your data, and "
                "that they are not missing in a non-default column_keys list in the yaml config "
                "file."
            )
        self.allow_delta = len(self.ensembles) > 1
        self.set_callbacks(app)

    @property
    def ens_colors(self):
        return unique_colors(self.ensembles, self.theme)

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard displaying reservoir simulation time series.",
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Visualization of selected time series. "
                    "Different options can be set in the menu to the left."
                ),
            },
            {
                "id": self.uuid("ensemble"),
                "content": (
                    "Display time series from one or several ensembles. "
                    "Different ensembles will be overlain in the same plot."
                ),
            },
            {
                "id": self.uuid("vectors"),
                "content": (
                    "Display up to three different time series. "
                    "Each time series will be visualized in a separate plot."
                ),
            },
            {
                "id": self.uuid("visualization"),
                "content": (
                    "Choose between different visualizations. 1. Show time series as "
                    "individual lines per realization. 2. Show statistical fanchart per "
                    "ensemble. 3. Show statistical fanchart per ensemble and histogram "
                    "per date. Select a data by clicking in the plot."
                ),
            },
        ]

    @staticmethod
    def set_grid_layout(columns, padding=0):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
            "padding": f"{padding}px",
        }

    @property
    def delta_layout(self):
        show_delta = "block" if self.allow_delta else "none"
        return html.Div(
            children=[
                html.Div(
                    style={"display": show_delta},
                    children=html.Label(
                        children=[
                            html.Span("Mode:", style={"font-weight": "bold"}),
                            dcc.RadioItems(
                                id=self.uuid("mode"),
                                style={"marginBottom": "25px"},
                                options=[
                                    {
                                        "label": "Individual ensembles",
                                        "value": "ensembles",
                                    },
                                    {
                                        "label": "Delta between ensembles",
                                        "value": "delta_ensembles",
                                    },
                                ],
                                value="ensembles",
                            ),
                        ]
                    ),
                ),
                html.Div(
                    id=self.uuid("show_ensembles"),
                    children=html.Label(
                        children=[
                            html.Span(
                                "Selected ensembles:", style={"font-weight": "bold"}
                            ),
                            dcc.Dropdown(
                                id=self.uuid("ensemble"),
                                clearable=False,
                                multi=True,
                                options=[
                                    {"label": i, "value": i} for i in self.ensembles
                                ],
                                value=self.ensembles[0],
                            ),
                        ],
                    ),
                ),
                html.Div(
                    id=self.uuid("calc_delta"),
                    style={"display": "none"},
                    children=[
                        html.Span(
                            "Selected ensemble delta (A-B):",
                            style={"font-weight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                html.Div(
                                    [
                                        html.Label(
                                            style={"fontSize": "12px"},
                                            children="Ensemble A",
                                        ),
                                        dcc.Dropdown(
                                            id=self.uuid("base_ens"),
                                            clearable=False,
                                            options=[
                                                {"label": i, "value": i}
                                                for i in self.ensembles
                                            ],
                                            value=self.ensembles[0],
                                        ),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Label(
                                            style={"fontSize": "12px"},
                                            children="Ensemble B",
                                        ),
                                        dcc.Dropdown(
                                            id=self.uuid("delta_ens"),
                                            clearable=False,
                                            options=[
                                                {"label": i, "value": i}
                                                for i in self.ensembles
                                            ],
                                            value=self.ensembles[-1],
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=[
                        self.delta_layout,
                        html.Div(
                            id=self.uuid("vectors"),
                            style={"marginTop": "25px"},
                            children=[
                                html.Span(
                                    "Time series:", style={"font-weight": "bold"}
                                ),
                                dcc.Dropdown(
                                    style={
                                        "marginTop": "5px",
                                        "marginBottom": "5px",
                                        "fontSize": ".95em",
                                    },
                                    optionHeight=55,
                                    id=self.uuid("vector1"),
                                    clearable=False,
                                    multi=False,
                                    options=self.dropdown_options,
                                    value=self.plot_options.get(
                                        "vector1", self.smry_cols[0]
                                    ),
                                ),
                                dcc.Dropdown(
                                    style={"marginBottom": "5px", "fontSize": ".95em"},
                                    optionHeight=55,
                                    id=self.uuid("vector2"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector2", None),
                                ),
                                dcc.Dropdown(
                                    style={"fontSize": ".95em"},
                                    optionHeight=55,
                                    id=self.uuid("vector3"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector3", None),
                                ),
                            ],
                        ),
                        html.Div(
                            id=self.uuid("visualization"),
                            style={"marginTop": "25px"},
                            children=[
                                html.Span(
                                    "Visualization:", style={"font-weight": "bold"}
                                ),
                                dcc.RadioItems(
                                    id=self.uuid("statistics"),
                                    options=[
                                        {
                                            "label": "Individual realizations",
                                            "value": "realizations",
                                        },
                                        {
                                            "label": "Statistical fanchart",
                                            "value": "statistics",
                                        },
                                        {
                                            "label": "Statistical fanchart and histogram",
                                            "value": "statistics_hist",
                                        },
                                    ],
                                    value=self.plot_options.get(
                                        "visualization", "statistics"
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            style={"height": "300px"},
                            children=wcc.Graph(id=self.uuid("graph"),),
                        ),
                        dcc.Store(
                            id=self.uuid("date"),
                            data=json.dumps(self.plot_options.get("date", None)),
                        ),
                    ],
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("vector1"), "value"),
                Input(self.uuid("vector2"), "value"),
                Input(self.uuid("vector3"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("mode"), "value"),
                Input(self.uuid("base_ens"), "value"),
                Input(self.uuid("delta_ens"), "value"),
                Input(self.uuid("statistics"), "value"),
                Input(self.uuid("date"), "data"),
            ],
        )
        # pylint: disable=too-many-instance-attributes, too-many-arguments, too-many-locals, too-many-branches
        def _update_graph(
            vector1,
            vector2,
            vector3,
            ensembles,
            calc_mode,
            base_ens,
            delta_ens,
            visualization,
            stored_date,
        ):
            """Callback to update all graphs based on selections"""

            # Combine selected vectors
            vectors = [vector1]
            if vector2:
                vectors.append(vector2)
            if vector3:
                vectors.append(vector3)

            # Ensure selected ensembles is a list
            ensembles = ensembles if isinstance(ensembles, list) else [ensembles]

            # Retrieve previous/current selected date
            date = json.loads(stored_date) if stored_date else None

            # Titles for subplots
            titles = []
            for vect in vectors:
                if self.smry_meta is None:
                    titles.append(simulation_vector_description(vect))
                else:
                    titles.append(
                        f"{simulation_vector_description(vect)}"
                        f" [{simulation_unit_reformat(self.smry_meta.unit[vect])}]"
                    )
                if visualization == "statistics_hist":
                    titles.append(date)

            # Make a plotly subplot figure
            fig = make_subplots(
                rows=len(vectors),
                cols=2 if visualization == "statistics_hist" else 1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=titles,
            )

            if calc_mode == "ensembles":
                data = filter_df(self.smry, ensembles, vectors, self.smry_meta)
            elif calc_mode == "delta_ensembles":
                data = filter_df(
                    self.smry, [base_ens, delta_ens], vectors, self.smry_meta
                )
                data = calculate_delta(data, base_ens, delta_ens)
            else:
                raise PreventUpdate

            if visualization in ["statistics", "statistics_hist"]:
                stat_df = calc_series_statistics(data, vectors)

            # Loop through each vector and calculate relevant plot
            legends = []
            for i, vector in enumerate(vectors):
                line_shape = get_simulation_line_shape(
                    line_shape_fallback=self.line_shape_fallback,
                    vector=vector,
                    smry_meta=self.smry_meta,
                )

                if visualization in ["statistics", "statistics_hist"]:
                    traces = add_statistic_traces(
                        stat_df, vector, colors=self.ens_colors, line_shape=line_shape,
                    )
                    if visualization == "statistics_hist":
                        histdata = add_histogram_traces(
                            data, vector, date=date, colors=self.ens_colors
                        )
                        for trace in histdata:
                            fig.add_trace(trace, i + 1, 2)
                elif visualization == "realizations":
                    traces = add_realization_traces(
                        data, vector, colors=self.ens_colors, line_shape=line_shape,
                    )
                else:
                    raise PreventUpdate

                if (
                    historical_vector(vector=vector, smry_meta=self.smry_meta)
                    in data.columns
                ):
                    traces.append(
                        add_history_trace(
                            data,
                            historical_vector(vector=vector, smry_meta=self.smry_meta),
                            line_shape,
                        )
                    )

                # Remove unwanted legends(only keep one for each ensemble)
                for trace in traces:
                    if trace.get("showlegend"):
                        if trace.get("legendgroup") in legends:
                            trace["showlegend"] = False
                        else:
                            legends.append(trace.get("legendgroup"))
                    fig.add_trace(trace, i + 1, 1)
                # Add observations
                if calc_mode != "delta_ensembles" and self.observations.get(vector):
                    for trace in add_observation_trace(self.observations.get(vector)):
                        fig.add_trace(trace, i + 1, 1)

            fig = fig.to_dict()
            fig["layout"].update(
                height=800,
                margin={"t": 20, "b": 0},
                barmode="overlay",
                bargap=0.01,
                bargroupgap=0.2,
            )
            fig["layout"] = self.theme.create_themed_layout(fig["layout"])

            if visualization == "statistics_hist":
                # Remove linked x-axis for histograms
                if "xaxis2" in fig["layout"]:
                    fig["layout"]["xaxis2"]["matches"] = None
                    fig["layout"]["xaxis2"]["showticklabels"] = True
                if "xaxis4" in fig["layout"]:
                    fig["layout"]["xaxis4"]["matches"] = None
                    fig["layout"]["xaxis4"]["showticklabels"] = True
                if "xaxis6" in fig["layout"]:
                    fig["layout"]["xaxis6"]["matches"] = None
                    fig["layout"]["xaxis6"]["showticklabels"] = True
            return fig

        @app.callback(
            self.plugin_data_output,
            [self.plugin_data_requested],
            [
                State(self.uuid("vector1"), "value"),
                State(self.uuid("vector2"), "value"),
                State(self.uuid("vector3"), "value"),
                State(self.uuid("ensemble"), "value"),
                State(self.uuid("mode"), "value"),
                State(self.uuid("base_ens"), "value"),
                State(self.uuid("delta_ens"), "value"),
                State(self.uuid("statistics"), "value"),
            ],
        )
        def _user_download_data(
            data_requested,
            vector1,
            vector2,
            vector3,
            ensembles,
            calc_mode,
            base_ens,
            delta_ens,
            visualization,
        ):
            """Callback to download data based on selections"""

            # Combine selected vectors
            vectors = [vector1]
            if vector2:
                vectors.append(vector2)
            if vector3:
                vectors.append(vector3)

            if calc_mode == "ensembles":
                # Ensure selected ensembles is a list
                ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
                data = filter_df(self.smry, ensembles, vectors, self.smry_meta)
            elif calc_mode == "delta_ensembles":
                data = filter_df(
                    self.smry, [base_ens, delta_ens], vectors, self.smry_meta
                )
                data = calculate_delta(data, base_ens, delta_ens)
            else:
                raise PreventUpdate

            if visualization in ["statistics", "statistics_hist"]:
                data = calc_series_statistics(data, vectors)
                data = data.sort_values(by=[("", "ENSEMBLE"), ("", "DATE")])
            else:
                data = data.sort_values(by=["ENSEMBLE", "REAL", "DATE"])
                # Reorder columns
                data = data[
                    ["ENSEMBLE", "REAL", "DATE"]
                    + [
                        col
                        for col in data.columns
                        if col not in ["ENSEMBLE", "REAL", "DATE"]
                    ]
                ]

            return (
                WebvizPluginABC.plugin_data_compress(
                    [
                        {
                            "filename": "reservoir_simulation_timeseries.csv",
                            "content": data.to_csv(index=False),
                        }
                    ]
                )
                if data_requested
                else ""
            )

        @app.callback(
            [
                Output(self.uuid("show_ensembles"), "style"),
                Output(self.uuid("calc_delta"), "style"),
            ],
            [Input(self.uuid("mode"), "value")],
        )
        def _update_mode(mode):
            """Switch displayed ensemble selector for delta/no-delta"""
            if mode == "ensembles":
                style = {"display": "block"}, {"display": "none"}
            else:
                style = {"display": "none"}, {"display": "block"}
            return style

        @app.callback(
            Output(self.uuid("date"), "data"),
            [Input(self.uuid("graph"), "clickData")],
            [State(self.uuid("date"), "data")],
        )
        def _update_date(clickdata, date):
            """Store clicked date for use in other callback"""
            date = clickdata["points"][0]["x"] if clickdata else json.loads(date)
            return json.dumps(date)

    def add_webvizstore(self):
        functions = []
        if self.csvfile:
            functions.append((read_csv, [{"csv_file": self.csvfile}]))
        else:
            functions.append(
                (
                    load_smry,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "time_index": self.time_index,
                            "column_keys": self.column_keys,
                        }
                    ],
                )
            )
            functions.append(
                (
                    load_smry_meta,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "column_keys": self.column_keys,
                        }
                    ],
                )
            )
        if self.obsfile:
            functions.append((get_path, [{"path": self.obsfile}]))
        return functions


def format_observations(obslist):
    try:
        return {item.pop("key"): item for item in obslist}
    except KeyError:
        raise KeyError("Observation file has invalid format")


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensembles, vectors, smry_meta):
    """Filter dataframe for current vector. Include history
    vector if present"""
    columns = ["REAL", "ENSEMBLE", "DATE"] + vectors
    for vector in vectors:
        if historical_vector(vector=vector, smry_meta=smry_meta) in df.columns:
            columns.append(historical_vector(vector=vector, smry_meta=smry_meta))

    return df.loc[df["ENSEMBLE"].isin(ensembles)][columns]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_delta(df, base_ens, delta_ens):
    """Calculate delta between two ensembles"""
    base_df = (
        df.loc[df["ENSEMBLE"] == base_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    delta_df = (
        df.loc[df["ENSEMBLE"] == delta_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    dframe = base_df.sub(delta_df).reset_index()
    dframe["ENSEMBLE"] = f"({base_ens}) - ({delta_ens})"
    return dframe.fillna(0)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_histogram_traces(dframe, vector, date, colors):
    """Renders a histogram trace per ensemble for a given date"""
    dframe["DATE"] = dframe["DATE"].astype(str)
    data = dframe.loc[dframe["DATE"] == date]

    return [
        {
            "type": "histogram",
            "x": list(ens_df[vector]),
            "name": ensemble,
            "marker": {
                "color": colors.get(ensemble, colors[list(colors.keys())[0]]),
                "line": {"color": "black", "width": 1},
            },
            "showlegend": False,
        }
        for ensemble, ens_df in data.groupby("ENSEMBLE")
    ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_observation_trace(obs):
    return [
        {
            "x": [value.get("date"), []],
            "y": [value.get("value"), []],
            "marker": {"color": "black"},
            "text": value.get("comment", None),
            "hoverinfo": "y+x+text",
            "showlegend": False,
            "error_y": {
                "type": "data",
                "array": [value.get("error"), []],
                "visible": True,
            },
        }
        for value in obs.get("observations", [])
    ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_realization_traces(dframe, vector, colors, line_shape):
    """Renders line trace for each realization, includes history line if present"""
    return [
        {
            "line": {"shape": line_shape},
            "x": list(real_df["DATE"]),
            "y": list(real_df[vector]),
            "hovertext": f"Realization: {real_no}, Ensemble: {ensemble}",
            "name": ensemble,
            "legendgroup": ensemble,
            "marker": {"color": colors.get(ensemble, colors[list(colors.keys())[0]])},
            "showlegend": real_no == 0,
        }
        for ens_no, (ensemble, ens_df) in enumerate(dframe.groupby("ENSEMBLE"))
        for real_no, (real, real_df) in enumerate(ens_df.groupby("REAL"))
    ]


def add_history_trace(dframe, vector, line_shape):
    """Renders the history line"""
    df = dframe.loc[
        (dframe["REAL"] == dframe["REAL"].unique()[0])
        & (dframe["ENSEMBLE"] == dframe["ENSEMBLE"].unique()[0])
    ]
    return {
        "line": {"shape": line_shape},
        "x": df["DATE"],
        "y": df[vector],
        "hovertext": "History",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "black"},
        "showlegend": True,
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_statistic_traces(stat_df, vector, colors, line_shape):
    """Add fanchart traces for selected vector"""
    traces = []
    for ensemble, ens_df in stat_df.groupby(("", "ENSEMBLE")):
        traces.extend(
            add_fanchart_traces(
                ens_df,
                vector,
                colors.get(ensemble, colors[list(colors.keys())[0]]),
                ensemble,
                line_shape,
            )
        )
    return traces


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


@webvizstore
def get_path(path) -> Path:
    return Path(path)
