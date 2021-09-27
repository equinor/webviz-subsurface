import json
from typing import Callable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._datainput.fmu_input import load_ensemble_set, load_parameters


class RunningTimeAnalysisFMU(WebvizPluginABC):
    """Can e.g. be used to investigate which jobs that are important for the running
time of realizations, and if specific parameter combinations increase running time or chance of
realization failure. Systematic realization failure could introduce bias to assisted history
matching.

Visualizations:
* Running time matrix, a heatmap of job running times relative to:
    * Same job in ensemble
    * Slowest job in ensemble
    * Slowest job in realization
* Parameter parallel coordinates plot:
    * Analyze running time and successful/failed run together with input parameters.

---

* **`ensembles`:** Which ensembles in `shared_settings` to include in check. Only required input.
* **`filter_shorter`:** Filters jobs with maximum run time in ensemble less than X seconds \
    (default: 10). Can be checked on/off interactively, this only sets the filtering value.
* **`status_file`:** Name of json file local per realization with job status \
    (default: `status.json`).
* **`visual_parameters`:** List of default visualized parameteres in parallel coordinates plot \
    (default: all parameters).

---

Parameters are picked up automatically from `parameters.txt` in individual realizations in
defined ensembles using `fmu-ensemble`.

The `status.json` file is the standard status file when running
[`ERT`](https://github.com/Equinor/ert) runs. If defining a different name, it still has to be
on the same format [(example file)](https://github.com/equinor/webviz-subsurface-testdata/\
blob/master/reek_history_match/realization-0/iter-0/status.json).
"""

    COLOR_MATRIX_BY_LABELS = [
        "Same job in ensemble",
        "Slowest job in realization",
        "Slowest job in ensemble",
    ]

    COLOR_PARCOORD_BY_LABELS = [
        "Successful/failed realization",
        "Running time of realization",
    ]

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        filter_shorter: Union[int, float] = 10,
        status_file: str = "status.json",
        visual_parameters: Optional[list] = None,
    ):
        super().__init__()
        self.filter_shorter = filter_shorter
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.ensembles = ensembles
        self.status_file = status_file
        self.parameter_df = load_parameters(
            ensemble_paths=self.ens_paths,
            ensemble_set_name="EnsembleSet",
            filter_file=None,
        )
        all_data_df = make_status_df(
            self.ens_paths, self.status_file
        )  # Has to be stored in one df due to webvizstore, see issue #206 in webviz-config
        self.job_status_df = all_data_df.loc["job"]
        self.real_status_df = all_data_df.loc["real"]
        self.visual_parameters = (
            visual_parameters if visual_parameters else self.parameters
        )
        self.set_callbacks(app)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("mode"),
                "content": (
                    "Switch between job running time matrix and parameter parallel coordinates."
                ),
            },
            {
                "id": self.uuid("ensemble"),
                "content": ("Display the realizations from the selected ensemble. "),
            },
            {
                "id": self.uuid("relative_runtime"),
                "content": ("Make the colorscale relative to the selected option."),
            },
        ]

    @property
    def parameters(self) -> List[str]:
        """Returns numerical input parameters"""
        return list(
            self.parameter_df.drop(["ENSEMBLE", "REAL"], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )

    @property
    def plot_fig(self) -> html.Div:
        return html.Div(
            style={
                "overflowX": "hidden",
                "width": "100%",
            },
            children=[
                html.Div(
                    id=self.uuid("plot_fig"),
                    style={"overflowX": "auto", "width": "100%"},
                    children=wcc.Graph(id=self.uuid("fig")),
                ),
                # Blank div: Makes sure that horizontal scrollbar is moved straight under the
                # figure instead of the figure div getting padded by whitespace down to height of
                # outer div.
                html.Div(style={"width": "100%"}),
            ],
        )

    @property
    def control_div(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Selectors(
                    label="Mode",
                    children=[
                        wcc.RadioItems(
                            id=self.uuid("mode"),
                            options=[
                                {
                                    "label": "Running time matrix",
                                    "value": "running_time_matrix",
                                },
                                {
                                    "label": "Parameter parallel coordinates",
                                    "value": "parallel_coordinates",
                                },
                            ],
                            value="running_time_matrix",
                        ),
                    ],
                ),
                wcc.Selectors(
                    label="Ensemble",
                    children=[
                        wcc.Dropdown(
                            id=self.uuid("ensemble"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles[0],
                            clearable=False,
                        ),
                    ],
                ),
                wcc.Selectors(
                    label="Coloring",
                    children=[
                        html.Div(
                            id=self.uuid("matrix_color"),
                            children=[
                                wcc.Dropdown(
                                    label="Color jobs relative to running time of:",
                                    id=self.uuid("relative_runtime"),
                                    options=[
                                        {"label": rel, "value": rel}
                                        for rel in RunningTimeAnalysisFMU.COLOR_MATRIX_BY_LABELS
                                    ],
                                    value=RunningTimeAnalysisFMU.COLOR_MATRIX_BY_LABELS[
                                        0
                                    ],
                                    clearable=False,
                                ),
                            ],
                        ),
                        html.Div(
                            id=self.uuid("parcoords_color"),
                            style={"display": "none"},
                            children=[
                                wcc.Dropdown(
                                    label="Color realizations relative to:",
                                    id=self.uuid("relative_real"),
                                    options=[
                                        {"label": rel, "value": rel}
                                        for rel in RunningTimeAnalysisFMU.COLOR_PARCOORD_BY_LABELS
                                    ],
                                    value=RunningTimeAnalysisFMU.COLOR_PARCOORD_BY_LABELS[
                                        0
                                    ],
                                    clearable=False,
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Selectors(
                    label="Filtering",
                    children=[
                        html.Div(
                            id=self.uuid("parameter_dropdown"),
                            style={"display": "none"},
                            children=[
                                wcc.SelectWithLabel(
                                    id=self.uuid("parameters"),
                                    style={"overflowX": "auto", "fontSize": "0.97rem"},
                                    options=[
                                        {"label": param, "value": param}
                                        for param in self.parameters
                                    ],
                                    multi=True,
                                    value=self.visual_parameters,
                                    size=min(50, len(self.visual_parameters)),
                                ),
                            ],
                        ),
                        html.Div(
                            id=self.uuid("filter_short_checkbox"),
                            children=[
                                wcc.Checklist(
                                    label="Filter jobs",
                                    id=self.uuid("filter_short"),
                                    options=[
                                        {
                                            "label": "Slowest in ensemble less than "
                                            f"{self.filter_shorter}s",
                                            "value": "filter_short",
                                        },
                                    ],
                                    value=["filter_short"],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                wcc.Frame(
                    style={"flex": "1", "height": "90vh"}, children=self.control_div
                ),
                wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"flex": "6", "height": "90vh"},
                    children=self.plot_fig,
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("fig"), "figure"),
            [
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("mode"), "value"),
                Input(self.uuid("relative_runtime"), "value"),
                Input(self.uuid("relative_real"), "value"),
                Input(self.uuid("parameters"), "value"),
                Input(self.uuid("filter_short"), "value"),
            ],
        )
        def _update_fig(
            ens: str,
            mode: str,
            rel_runtime: str,
            rel_real: str,
            params: Union[str, List[str]],
            filter_short: List[str],
        ) -> dict:
            """Update main figure
            Dependent on `mode` it will call rendering of the chosen form of visualization
            """
            if mode == "running_time_matrix" and "filter_short" in filter_short:
                return render_matrix(
                    self.job_status_df[
                        (self.job_status_df["ENSEMBLE"] == ens)
                        & (self.job_status_df["JOB_MAX_RUNTIME"] >= self.filter_shorter)
                    ],
                    rel_runtime,
                    self.plotly_theme,
                )
            if mode == "running_time_matrix":
                return render_matrix(
                    self.job_status_df[(self.job_status_df["ENSEMBLE"] == ens)],
                    rel_runtime,
                    self.plotly_theme,
                )

            # Otherwise: parallel coordinates
            # Ensure selected parameters is a list
            params = params if isinstance(params, list) else [params]
            # Color by success or runtime, for runtime drop unsuccesful
            colormap_labels: Union[List[str], None]
            if rel_real == "Successful/failed realization":
                plot_df = self.real_status_df[self.real_status_df["ENSEMBLE"] == ens]
                colormap = make_colormap(
                    self.plotly_theme["layout"]["colorway"], discrete=2
                )
                color_by_col = "STATUS_BOOL"
                colormap_labels = ["Failed", "Success"]
            else:
                plot_df = self.real_status_df[
                    (self.real_status_df["ENSEMBLE"] == ens)
                    & (self.real_status_df["STATUS_BOOL"] == 1)
                ]
                colormap = self.plotly_theme["layout"]["colorscale"]["sequential"]
                color_by_col = "RUNTIME"
                colormap_labels = None

            # Call rendering of parallel coordinate plot
            return render_parcoord(
                plot_df,
                params,
                self.plotly_theme,
                colormap,
                color_by_col,
                colormap_labels,
            )

        @app.callback(
            [
                Output(self.uuid("matrix_color"), "style"),
                Output(self.uuid("parcoords_color"), "style"),
                Output(self.uuid("parameter_dropdown"), "style"),
                Output(self.uuid("filter_short_checkbox"), "style"),
            ],
            [Input(self.uuid("mode"), "value")],
        )
        def _update_mode(mode: str) -> Tuple[dict, dict, dict, dict]:
            """Switch displayed mode between running time matrix and parallel coordinates"""
            if mode == "running_time_matrix":
                style = (
                    {"display": "block"},
                    {"display": "none"},
                    {"display": "none"},
                    {"display": "block"},
                )
            else:
                style = (
                    {"display": "none"},
                    {"display": "block"},
                    {"display": "block"},
                    {"display": "none"},
                )
            return style

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (
                make_status_df,
                [
                    {
                        "ens_paths": self.ens_paths,
                        "status_file": self.status_file,
                    }
                ],
            ),
            (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "filter_file": None,
                    },
                ],
            ),
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(status_df: pd.DataFrame, rel: str, theme: dict) -> dict:
    """Render matrix
    Returns figure object as heatmap for the chosen ensemble and scaling method.
    """
    if rel == "Same job in ensemble":
        z = list(status_df["JOB_SCALED_RUNTIME"])
    elif rel == "Slowest job in realization":
        z = list(status_df["REAL_SCALED_RUNTIME"])
    else:
        z = list(status_df["ENS_SCALED_RUNTIME"])
    data = {
        "type": "heatmap",
        "x": list(status_df["REAL"]),
        "y": list(status_df["JOB_ID"]),
        "z": z,
        "zmin": 0,
        "zmax": 1,
        "text": list(status_df["HOVERINFO"]),
        "hoverinfo": "text",
        "colorscale": theme["layout"]["colorscale"]["sequential"],
        "colorbar": {
            "tickvals": [
                0,
                0.5,
                1,
            ],
            "ticktext": [
                "0 %",
                "50 %",
                "100 %",
            ],
            "xanchor": "left",
        },
    }
    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {
                "t": 50,
                "b": 50,
                "l": 50,
            },
            "xaxis": {
                "ticks": "",
                "title": "Realizations",
                "showgrid": False,
                "side": "top",
            },
            "yaxis": {
                "ticks": "",
                "showticklabels": True,
                "tickmode": "array",
                "tickvals": list(status_df["JOB_ID"]),
                "ticktext": list(status_df["JOB"]),
                "showgrid": False,
                "automargin": True,
                "autorange": "reversed",
                "type": "category",
            },
            "height": max(350, len(status_df["JOB_ID"].unique()) * 15),
            "width": max(400, len(status_df["REAL"].unique()) * 12 + 250),
        }
    )

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_parcoord(
    plot_df: pd.DataFrame,
    params: List[str],
    theme: dict,
    colormap: Union[List[str], List[list]],
    color_col: str,
    colormap_labels: Union[List[str], None] = None,
) -> dict:
    """Renders parallel coordinates plot"""
    # Create parcoords dimensions (one per parameter)
    dimensions = [
        {"label": param, "values": plot_df[param].values.tolist()} for param in params
    ]

    # Parcoords data dict
    data: dict = {
        "line": {
            "color": plot_df[color_col].values.tolist(),
            "colorscale": colormap,
            "showscale": True,
        },
        "dimensions": dimensions,
        "labelangle": -90,
        "labelside": "bottom",
        "type": "parcoords",
    }
    if color_col == "STATUS_BOOL":
        data["line"].update(
            {
                "cmin": -0.5,
                "cmax": 1.5,
                "colorbar": {
                    "tickvals": [0, 1],
                    "ticktext": colormap_labels,
                    "title": "Status",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.3,
                },
            },
        )
    else:
        data["line"].update(
            {
                "colorbar": {
                    "title": "Running time",
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
        )

    layout = {}
    layout.update(theme["layout"])
    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 100 + 250
    margin_b = max([len(param) for param in params]) * 8
    layout.update({"width": width, "height": 800, "margin": {"b": margin_b, "t": 30}})
    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
def make_status_df(
    ens_paths: dict,
    status_file: str,
) -> pd.DataFrame:
    """Return DataFrame of information from status.json files.
    *Finds status.json filepaths.
    For jobs:
    *Loads data into pandas DataFrames.
    *Calculates runtimes and normalized runtimes.
    *Creates hoverinfo column to be used in visualization.
    For realizations:
    *Creates DataFrame of success/failure and total running time.
    """

    parameter_df = load_parameters(
        ensemble_paths=ens_paths,
        ensemble_set_name="EnsembleSet",
        filter_file=None,
    )
    # sub-method to process ensemble data when all realizations in ensemble have been processed
    def ensemble_post_processing() -> list:
        # add missing realizations to get whitespace in heatmap matrix
        if len(set(range(min(reals), max(reals) + 1))) > len(set(reals)):
            missing_df = ens_dfs[0].copy()
            missing_df["STATUS"] = "Realization not started"
            missing_df["RUNTIME"] = np.NaN
            missing_df["JOB_SCALED_RUNTIME"] = np.NaN
            missing_df["ENS_SCALED_RUNTIME"] = np.NaN
            for missing_real in set(range(min(reals), max(reals) + 1)).difference(
                set(reals)
            ):
                ens_dfs.append(missing_df.copy())
                ens_dfs[-1]["REAL"] = missing_real
                ens_dfs[-1]["ENSEMBLE"] = ens
        # Concatenate realization DataFrames to an Ensemble DataFrame and store in list
        job_status_dfs.append(pd.concat(ens_dfs))
        # Find max running time of job in ensemble and create scaled columns
        job_status_dfs[-1]["JOB_MAX_RUNTIME"] = pd.concat(
            [ens_max_job_runtime] * (len(ens_dfs))
        )
        job_status_dfs[-1]["JOB_SCALED_RUNTIME"] = (
            job_status_dfs[-1]["RUNTIME"] / job_status_dfs[-1]["JOB_MAX_RUNTIME"]
        )
        job_status_dfs[-1]["ENS_SCALED_RUNTIME"] = job_status_dfs[-1][
            "RUNTIME"
        ] / np.amax(ens_max_job_runtime)
        # Return ensemble DataFrame list updated with the latest ensemble
        return job_status_dfs

    # find status filepaths
    ens_set = load_ensemble_set(ens_paths, filter_file=None)
    df = pd.concat(
        [
            ens_set[ens].find_files(status_file).assign(ENSEMBLE=ens)
            for ens in ens_set.ensemblenames
        ]
    )
    # Initial values for local variables
    job_status_dfs: list = []
    ens_dfs: list = []
    real_status: list = []
    ens_max_job_runtime = 1
    ens = ""
    reals: list = []

    # Loop through identified filepaths and get realization data
    for row in df.itertuples(index=False):
        # Load each json-file to a DataFrame for the realization
        with open(row.FULLPATH) as fjson:
            status_dict = json.load(fjson)
        real_df = pd.DataFrame(status_dict["jobs"])

        # If new ensemble, calculate ensemble scaled runtimes
        # for previous ensemble and reset temporary ensemble data
        if ens != row.ENSEMBLE:
            if ens == "":  # First ensemble
                ens = row.ENSEMBLE
            else:  # Store last ensemble and reset temporary ensemble data
                job_status_dfs = ensemble_post_processing()
                ens_max_job_runtime = 1
                ens_dfs = []
                ens = row.ENSEMBLE
                reals = []

        # Additional realization data into realization DataFrame
        real_df["RUNTIME"] = real_df["end_time"] - real_df["start_time"]
        real_df["REAL"] = row.REAL
        real_df["ENSEMBLE"] = row.ENSEMBLE
        real_df["REAL_SCALED_RUNTIME"] = real_df["RUNTIME"] / max(
            real_df["RUNTIME"].dropna()
        )
        real_df = real_df[
            ["ENSEMBLE", "REAL", "RUNTIME", "REAL_SCALED_RUNTIME", "name", "status"]
        ].rename(columns={"name": "JOB", "status": "STATUS"})
        # Status DataFrame to be used with parallel coordinates
        if all(real_df["STATUS"] == "Success"):
            real_status.append(
                {
                    "ENSEMBLE": row.ENSEMBLE,
                    "REAL": row.REAL,
                    "STATUS": "Success",
                    "STATUS_BOOL": 1,
                    "RUNTIME": status_dict["end_time"] - status_dict["start_time"],
                }
            )
        else:
            real_status.append(
                {
                    "ENSEMBLE": row.ENSEMBLE,
                    "REAL": row.REAL,
                    "STATUS": "Failure",
                    "STATUS_BOOL": 0,
                    "RUNTIME": None,
                }
            )

        # Need unique job ids names to separate jobs in same realization with same name in json file
        real_df["JOB_ID"] = range(0, len(real_df["JOB"]))

        # Update max runtime for jobs in ensemble
        ens_max_job_runtime = np.fmax(real_df["RUNTIME"], ens_max_job_runtime)

        # Append realization to ensemble data
        reals.append(row.REAL)
        ens_dfs.append(real_df)

    # Add last ensemble
    job_status_dfs = ensemble_post_processing()
    job_status_df = pd.concat(job_status_dfs, sort=False)

    # Create hoverinfo
    job_status_df["HOVERINFO"] = (
        "Real: "
        + job_status_df["REAL"].astype(str)
        + "<br>"
        + "Job: #"
        + job_status_df["JOB_ID"].astype(str)
        + "<br>"
        + job_status_df["JOB"].astype(str)
        + "<br>"
        + "Running time: "
        + job_status_df["RUNTIME"].astype(str)
        + " s"
        + "<br>"
        + "Status: "
        + job_status_df["STATUS"]
    )
    # Create dataframe of realization status and merge with realization parameters for parameter
    # parallel coordinates
    real_status_df = pd.DataFrame(real_status).merge(
        parameter_df, on=["ENSEMBLE", "REAL"]
    )
    # Has to be stored in one df due to webvizstore, see issue #206 in webviz-config
    return pd.concat([job_status_df, real_status_df], keys=["job", "real"], sort=False)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_colormap(color_array: list, discrete: int = None) -> list:
    """
    Returns a colormap:
    * If the `discrete` variable is set to an integer x, the colormap will be a discrete map of
    size x evenly sampled from the given color_array.
    * If discrete not defined or `None`: assumes continuous colormap and returns the given
    color_array.
    """
    if discrete is None:
        colormap = color_array
    else:
        colormap = []
        for i in range(0, discrete):
            colormap.append([i / discrete, color_array[i]])
            colormap.append([(i + 1) / discrete, color_array[i]])
    return colormap
