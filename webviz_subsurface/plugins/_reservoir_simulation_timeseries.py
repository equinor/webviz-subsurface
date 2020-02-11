from uuid import uuid4
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

from .._datainput.fmu_input import load_smry
from .._abbreviations import simulation_vector_description


def _historical_vector(vector, return_historical=True):
    """This is a unnecessary complex function, trying to make a best guess
    on converting between historical and non-historical vector names, while
    waiting for a robust/correct solution, e.g. something like
    https://github.com/equinor/fmu-ensemble/issues/87

    If return_historical is `True`, the corresponding guessed historical vector name
    is returned. If `False` the corresponding non-historical vector name is returned,
    but in this case if the input vector is not believed to be a historical vector,
    None is returned.
    """

    parts = vector.split(":", 1)

    if return_historical:
        parts[0] += "H"
        return ":".join(parts)

    if not parts[0].endswith("H"):
        return None

    parts[0] = parts[0][:-1]
    return ":".join(parts)


class ReservoirSimulationTimeSeries(WebvizPluginABC):
    """### ReservoirSimulationTimeSeries

Visualizes reservoir simulation time series for FMU ensembles.
Input can be given either as aggregated csv file or an ensemble defined
in plugin settings.

* `csvfile`: Aggregated csvfile for unsmry with 'REAL', 'ENSEMBLE', 'DATE' and vector columns
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `column_keys`: List of vectors to extract. If not given, all vectors
                 from the simulations will be extracted. Wild card asterisk *
                 can be used.
* `sampling`: Time separation between extracted values. Can be e.g. `monthly`
              or `yearly`.
* `options`: Options to initialize plots with. See below

Plot options:
    * `vector1` : First vector to display
    * `vector2` : Second vector to display
    * `vector3` : Third vector to display
    * `visualization` : 'realizations', 'statistics' or 'statistics_hist',
    * `date` : Date to show in histograms
"""

    ENSEMBLE_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]
    # pylint:disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        obsfile: Path = None,
        column_keys=None,
        sampling: str = "monthly",
        options: dict = None,
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
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )

        self.smry_cols = [
            c
            for c in self.smry.columns
            if c not in ReservoirSimulationTimeSeries.ENSEMBLE_COLUMNS
            and not _historical_vector(c, False) in self.smry.columns
        ]

        self.dropdown_options = [
            {"label": f"{simulation_vector_description(vec)} ({vec})", "value": vec}
            for vec in self.smry_cols
        ]

        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.plot_options = options if options else {}
        self.plot_options["date"] = (
            str(self.plot_options.get("date"))
            if self.plot_options.get("date")
            else None
        )
        self.allow_delta = len(self.ensembles) > 1
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def ens_colors(self):
        try:
            colors = self.plotly_theme["layout"]["colorway"]
        except KeyError:
            colors = self.plotly_theme.get(
                "colorway",
                [
                    "#243746",
                    "#eb0036",
                    "#919ba2",
                    "#7d0023",
                    "#66737d",
                    "#4c9ba1",
                    "#a44c65",
                    "#80b7bc",
                    "#ff1243",
                    "#919ba2",
                    "#be8091",
                    "#b2d4d7",
                    "#ff597b",
                    "#bdc3c7",
                    "#d8b2bd",
                    "#ffe7d6",
                    "#d5eaf4",
                    "#ff88a1",
                ],
            )
        return {ens: colors[self.ensembles.index(ens)] for ens in self.ensembles}

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": "Dashboard displaying reservoir simulation time series.",
            },
            {
                "id": self.ids("graph"),
                "content": (
                    "Visualization of selected time series. "
                    "Different options can be set in the menu to the left."
                ),
            },
            {
                "id": self.ids("ensemble"),
                "content": (
                    "Display time series from one or several ensembles. "
                    "Different ensembles will be overlain in the same plot."
                ),
            },
            {
                "id": self.ids("vectors"),
                "content": (
                    "Display up to three different time series. "
                    "Each time series will be visualized in a separate plot."
                ),
            },
            {
                "id": self.ids("visualization"),
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
                                id=self.ids("mode"),
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
                    id=self.ids("show_ensembles"),
                    children=html.Label(
                        children=[
                            html.Span(
                                "Selected ensembles:", style={"font-weight": "bold"}
                            ),
                            dcc.Dropdown(
                                id=self.ids("ensemble"),
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
                    id=self.ids("calc_delta"),
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
                                            id=self.ids("base_ens"),
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
                                            id=self.ids("delta_ens"),
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
        return html.Div(
            id=self.ids("layout"),
            style=self.set_grid_layout("1fr 4fr", padding=10),
            children=[
                html.Div(
                    children=[
                        html.Div(children=[self.delta_layout]),
                        html.Div(
                            id=self.ids("vectors"),
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
                                    id=self.ids("vector1"),
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
                                    id=self.ids("vector2"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector2", None),
                                ),
                                dcc.Dropdown(
                                    style={"fontSize": ".95em"},
                                    optionHeight=55,
                                    id=self.ids("vector3"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector3", None),
                                ),
                            ],
                        ),
                        html.Div(
                            id=self.ids("visualization"),
                            style={"marginTop": "25px"},
                            children=[
                                html.Span(
                                    "Visualization:", style={"font-weight": "bold"}
                                ),
                                dcc.RadioItems(
                                    id=self.ids("statistics"),
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
                    ]
                ),
                html.Div(
                    [
                        wcc.Graph(id=self.ids("graph")),
                        dcc.Store(
                            id=self.ids("date"),
                            data=json.dumps(self.plot_options.get("date", None)),
                        ),
                    ]
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("graph"), "figure"),
            [
                Input(self.ids("vector1"), "value"),
                Input(self.ids("vector2"), "value"),
                Input(self.ids("vector3"), "value"),
                Input(self.ids("ensemble"), "value"),
                Input(self.ids("mode"), "value"),
                Input(self.ids("base_ens"), "value"),
                Input(self.ids("delta_ens"), "value"),
                Input(self.ids("statistics"), "value"),
                Input(self.ids("date"), "data"),
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
                titles.append(simulation_vector_description(vect))
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

            # Loop through each vector and calculate relevant plot
            legends = []
            for i, vector in enumerate(vectors):
                if calc_mode == "ensembles":
                    data = filter_df(self.smry, ensembles, vector)
                elif calc_mode == "delta_ensembles":
                    data = filter_df(self.smry, [base_ens, delta_ens], vector)
                    data = calculate_delta(data, base_ens, delta_ens)
                else:
                    raise PreventUpdate

                if visualization == "statistics":
                    traces = add_statistic_traces(data, vector, colors=self.ens_colors)
                elif visualization == "realizations":
                    traces = add_realization_traces(
                        data, vector, colors=self.ens_colors
                    )
                elif visualization == "statistics_hist":
                    traces = add_statistic_traces(data, vector, colors=self.ens_colors)
                    histdata = add_histogram_traces(
                        data, vector, date=date, colors=self.ens_colors
                    )
                    for trace in histdata:
                        fig.add_trace(trace, i + 1, 2)
                else:
                    raise PreventUpdate

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

            # Add additional styling to layout
            fig["layout"].update(self.plotly_theme["layout"])
            fig["layout"].update(
                height=800,
                margin={"t": 20, "b": 0},
                barmode="overlay",
                bargap=0.01,
                bargroupgap=0.2,
            )

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
            [
                Output(self.ids("show_ensembles"), "style"),
                Output(self.ids("calc_delta"), "style"),
            ],
            [Input(self.ids("mode"), "value")],
        )
        def _update_mode(mode):
            """Switch displayed ensemble selector for delta/no-delta"""
            if mode == "ensembles":
                style = {"display": "block"}, {"display": "none"}
            else:
                style = {"display": "none"}, {"display": "block"}
            return style

        @app.callback(
            Output(self.ids("date"), "data"),
            [Input(self.ids("graph"), "clickData")],
            [State(self.ids("date"), "data")],
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
        if self.obsfile:
            functions.append((get_path, [{"path": self.obsfile}]))
        return functions


def format_observations(obslist):
    try:
        return {item.pop("key"): item for item in obslist}
    except KeyError:
        raise KeyError("Observation file has invalid format")


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensembles, vector):
    """Filter dataframe for current vector. Include history
    vector if present"""
    columns = ["REAL", "ENSEMBLE", vector, "DATE"]
    if _historical_vector(vector) in df.columns:
        columns.append(_historical_vector(vector))

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
def add_realization_traces(dframe, vector, colors):
    """Renders line trace for each realization, includes history line if present"""
    traces = [
        {
            # "type": "linegl",
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

    if _historical_vector(vector) in dframe.columns:
        traces.append(add_history_trace(dframe, _historical_vector(vector)))
    return traces


def add_history_trace(dframe, vector):
    """Renders the history line"""
    df = dframe.loc[
        (dframe["REAL"] == dframe["REAL"].unique()[0])
        & (dframe["ENSEMBLE"] == dframe["ENSEMBLE"].unique()[0])
    ]
    return {
        "x": df["DATE"],
        "y": df[vector],
        "hovertext": "History",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "black"},
        "showlegend": True,
    }


def add_statistic_traces(df, vector, colors):
    """Calculate statistics for a given vector for relevant ensembles"""
    quantiles = [10, 90]
    traces = []

    for ensemble, ens_df in df.groupby("ENSEMBLE"):
        dframe = ens_df.drop(columns=["ENSEMBLE", "REAL"]).groupby("DATE")

        # Build a dictionary of dataframes to be concatenated
        dframes = {}
        dframes["mean"] = dframe.mean()
        for quantile in quantiles:
            quantile_str = "p" + str(quantile)
            dframes[quantile_str] = dframe.quantile(q=quantile / 100.0)
        dframes["maximum"] = dframe.max()
        dframes["minimum"] = dframe.min()
        traces.extend(
            add_fanchart_traces(
                pd.concat(dframes, names=["STATISTIC"], sort=False)[vector],
                colors.get(ensemble, colors[list(colors.keys())[0]]),
                ensemble,
            )
        )
    if f"{vector}H" in df.columns:
        traces.append(add_history_trace(df, f"{vector}H"))
    return traces


def add_fanchart_traces(vector_stats, color, legend_group: str):
    """Renders a fanchart for an ensemble vector"""

    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "x": vector_stats["maximum"].index.tolist(),
            "y": vector_stats["maximum"].values,
            "mode": "lines",
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10",
            "x": vector_stats["p10"].index.tolist(),
            "y": vector_stats["p10"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "x": vector_stats["mean"].index.tolist(),
            "y": vector_stats["mean"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "P90",
            "x": vector_stats["p90"].index.tolist(),
            "y": vector_stats["p90"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "x": vector_stats["minimum"].index.tolist(),
            "y": vector_stats["minimum"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


@webvizstore
def get_path(path) -> Path:
    return Path(path)
