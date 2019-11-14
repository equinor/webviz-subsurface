from uuid import uuid4
import json
from pathlib import Path

import pandas as pd

import plotly.tools as tools
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc

import webviz_core_components as wcc
from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from ..datainput import load_smry

# pylint: disable=too-many-instance-attributes
class ReservoirSimulationTimeSeries(WebvizContainerABC):
    """### ReservoirSimulationTimeSeriesO

Visualizes reservoir simulation time series for FMU ensembles.
Input can be given either as aggregated csv file or an ensemble defined
in container settings.

* `csvfile`: Aggregated csvfile for unsmry with 'REAL', 'ENSEMBLE', 'DATE' and vector columns
* `ensembles`: Which ensembles in `container_settings` to visualize.
* `column_keys`: List of vectors to extract. If not given, all vectors
                 from the simulations will be extracted. Wild card asterisk *
                 can be used.
* `sampling`: Time separation between extracted values. Can be e.g. `monthly`
              or `yearly`.
* `options`: Options to initialize plots with. See below

Plot options:
    * 'vector1' : First vector to display
    * 'vector2' : Second vector to display
    * 'vector3' : Third vector to display
    * 'visualization' : 'realizations', 'statistics' or 'statistics_hist',
    * 'date' : Date to show in histograms
"""

    ENSEMBLE_COLUMNS = [
        "REAL",
        "ENSEMBLE",
        "DATE",
    ]

    def __init__(
        self,
        app,
        container_settings,
        csvfile: Path = None,
        ensembles: list = None,
        column_keys=None,
        sampling: str = "monthly",
        options: dict = None,
    ):
        self.csvfile = csvfile if csvfile else None
        self.time_index = sampling
        self.column_keys = tuple(column_keys) if column_keys else None
        if csvfile:
            self.smry = read_csv(csvfile)
        elif ensembles:
            self.ens_paths = tuple(
                (ensemble, container_settings["scratch_ensembles"][ensemble])
                for ensemble in ensembles
            )
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
            for c in [*self.smry.columns]
            if c not in ReservoirSimulationTimeSeries.ENSEMBLE_COLUMNS
            if not c.endswith("H")
        ]
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.plotly_layout = app.webviz_settings["plotly_layout"]
        self.plot_options = options if options else {}
        colors = self.plotly_layout.get(
            "colors",
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
        self.ens_colors = {
            ens: colors[self.ensembles.index(ens)] for ens in self.ensembles
        }

        self.allow_delta = len(self.ensembles) > 1
        self.make_uuids()
        self.set_callbacks(app)

    def make_uuids(self):
        uid = f"{uuid4()}"
        self.graph_id = f"graph_id-{uid}"
        self.vector_id = f"vector_id{uid}"
        self.vector2_id = f"vector2_id{uid}"
        self.vector3_id = f"vector3_id{uid}"
        self.ensemble_id = f"ensemble_id{uid}"
        self.base_ens_id = f"base_ens_id{uid}"
        self.delta_ens_id = f"delta_ens_id{uid}"
        self.mode_id = f"mode_id{uid}"
        self.calc_delta_id = f"calc_delta_id{uid}"
        self.show_ensembles_id = f"show_ensembles_id{uid}"
        self.statistics_id = f"statistics_id{uid}"
        self.date_id = f"date:id{uid}"

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def delta_layout(self):
        show_delta = "block" if self.allow_delta else "none"
        return html.Div(
            children=[
                html.Div(
                    style={"display": show_delta},
                    children=[
                        html.Label("Mode"),
                        dcc.RadioItems(
                            id=self.mode_id,
                            style={"marginBottom": "25px"},
                            options=[
                                {"label": "Show ensembles", "value": "ensembles"},
                                {
                                    "label": "Calculate ensemble deltas",
                                    "value": "delta_ensembles",
                                },
                            ],
                            value="ensembles",
                        ),
                    ],
                ),
                html.Div(
                    id=self.show_ensembles_id,
                    children=[
                        html.Label("Ensembles"),
                        dcc.Dropdown(
                            id=self.ensemble_id,
                            clearable=False,
                            multi=True,
                            options=[{"label": i, "value": i} for i in self.ensembles],
                            value=self.ensembles[0],
                        ),
                    ],
                ),
                html.Div(
                    id=self.calc_delta_id,
                    style={"display": "none"},
                    children=[
                        html.Label("Ensembles"),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                html.Div(
                                    [
                                        html.Label(
                                            style={"fontSize": "12px"}, children="Base"
                                        ),
                                        dcc.Dropdown(
                                            id=self.base_ens_id,
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
                                            style={"fontSize": "12px"}, children="Delta"
                                        ),
                                        dcc.Dropdown(
                                            id=self.delta_ens_id,
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
            ],
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 4fr"),
            children=[
                html.Div(
                    children=[
                        html.Div(
                            style={"padding": "10px"},
                            children=[
                                html.Div(children=[self.delta_layout],),
                                html.Label(
                                    style={"marginTop": "25px"}, children="Time Series"
                                ),
                                dcc.Dropdown(
                                    style={"marginTop": "5px", "marginBottom": "5px"},
                                    id=self.vector_id,
                                    clearable=False,
                                    multi=False,
                                    options=[
                                        {"label": i, "value": i} for i in self.smry_cols
                                    ],
                                    value=self.plot_options.get(
                                        "vector1", self.smry_cols[0]
                                    ),
                                ),
                                dcc.Dropdown(
                                    style={"marginBottom": "5px"},
                                    id=self.vector2_id,
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=[
                                        {"label": i, "value": i} for i in self.smry_cols
                                    ],
                                    value=self.plot_options.get("vector2", None),
                                ),
                                dcc.Dropdown(
                                    id=self.vector3_id,
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=[
                                        {"label": i, "value": i} for i in self.smry_cols
                                    ],
                                    value=self.plot_options.get("vector3", None),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"padding": "10px"},
                            children=[
                                html.Div("Visualization"),
                                dcc.RadioItems(
                                    id=self.statistics_id,
                                    options=[
                                        {
                                            "label": "Time series realization plot",
                                            "value": "realizations",
                                        },
                                        {
                                            "label": "Time series fanchart",
                                            "value": "statistics",
                                        },
                                        {
                                            "label": "Time series fanchart and histogram "
                                            "for a selected date",
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
                        wcc.Graph(id=self.graph_id),
                        dcc.Store(
                            id=self.date_id,
                            data=json.dumps(self.plot_options.get("date", None)),
                        ),
                    ]
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            Output(self.graph_id, "figure"),
            [
                Input(self.vector_id, "value"),
                Input(self.vector2_id, "value"),
                Input(self.vector3_id, "value"),
                Input(self.ensemble_id, "value"),
                Input(self.mode_id, "value"),
                Input(self.base_ens_id, "value"),
                Input(self.delta_ens_id, "value"),
                Input(self.statistics_id, "value"),
                Input(self.date_id, "data"),
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

            # Retrieve previous/current selected date
            date = json.loads(stored_date) if stored_date else None

            # Titles for subplots
            titles = []
            for vect in vectors:
                titles.append(vect)
                if visualization == "statistics_hist":
                    titles.append(date)

            fig = tools.make_subplots(
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
                    ensembles = (
                        ensembles if isinstance(ensembles, list) else [ensembles]
                    )
                    data = filter_df(self.smry, ensembles, vector)
                elif calc_mode == "delta_ensembles":
                    data = filter_df(self.smry, [base_ens, delta_ens], vector)
                    data = delta_vector(data, base_ens, delta_ens)
                else:
                    raise PreventUpdate

                if visualization == "statistics":
                    traces = render_statistics(data, vector, colors=self.ens_colors)
                elif visualization == "realizations":
                    traces = render_realizations(data, vector, colors=self.ens_colors)
                elif visualization == "statistics_hist":
                    traces = render_statistics(data, vector, colors=self.ens_colors)
                    histdata = render_histogram(
                        data, vector, date=date, colors=self.ens_colors
                    )

                    for trace in histdata:
                        fig.append_trace(trace, i + 1, 2)
                else:
                    raise PreventUpdate

                # Renaming unwanted legends(only keep one for each ensemble)
                for trace in traces:
                    if trace.get("showlegend"):
                        if trace.get("legendgroup") in legends:
                            trace["showlegend"] = False
                        else:
                            legends.append(trace.get("legendgroup"))
                    fig.append_trace(trace, i + 1, 1)

            # Add additional styling to layout
            fig["layout"].update(
                height=800,
                font=self.plotly_layout.get("font"),
                hoverlabel=self.plotly_layout.get("hoverlabel"),
                margin={"t": 20, "b": 0},
                barmode="overlay",
                bargap=0.01,
                bargroupgap=0.2,
            )

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
                Output(self.show_ensembles_id, "style"),
                Output(self.calc_delta_id, "style"),
            ],
            [Input(self.mode_id, "value")],
        )
        def _update_mode(mode):
            """Switch displayed ensemble selector for delta/no-delta"""
            if mode == "ensembles":
                style = {"display": "block"}, {"display": "none"}
            else:
                style = {"display": "none"}, {"display": "block"}
            return style

        @app.callback(
            Output(self.date_id, "data"),
            [Input(self.graph_id, "clickData")],
            [State(self.date_id, "data")],
        )
        def _update_date(clickdata, date):
            """Store clicked date for use in other callback"""
            date = clickdata["points"][0]["x"] if clickdata else json.loads(date)
            return json.dumps(date)

    def add_webvizstore(self):
        return (
            [(read_csv, [{"csv_file": self.csvfile}],)]
            if self.csvfile
            else [
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
            ]
        )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensembles, vector):
    """Filter dataframe for current vector. Include history
    vector if present"""
    columns = ["REAL", "ENSEMBLE", vector, "DATE"]
    if f"{vector}H" in df.columns:
        columns.append(f"{vector}H")
    return df.loc[df["ENSEMBLE"].isin(ensembles)][columns]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def delta_vector(df, base_ens, delta_ens):
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
    dframe["ENSEMBLE"] = f"{base_ens}-{delta_ens}"
    return dframe.fillna(0)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_histogram(dframe, vector, date, colors):
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
def render_realizations(dframe, vector, colors):
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

    if f"{vector}H" in dframe.columns:
        traces.append(render_history_trace(dframe, f"{vector}H"))
    return traces


def render_history_trace(dframe, vector):
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


def render_statistics(df, vector, colors):
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
            render_statistic_trace(
                pd.concat(dframes, names=["STATISTIC"], sort=False)[vector],
                colors.get(ensemble, colors[list(colors.keys())[0]]),
                ensemble,
            )
        )
    if f"{vector}H" in df.columns:
        traces.append(render_history_trace(df, f"{vector}H"))
    return traces


def render_statistic_trace(vector_stats, color, legend_group: str):
    """Renders a fanchart for an ensemble vector"""

    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    return [
        {
            "name": "maximum",
            "x": vector_stats["maximum"].index.tolist(),
            "y": vector_stats["maximum"].values,
            "mode": "lines",
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": "p10",
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
            "name": "p90",
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
            "name": "minimum",
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
