from uuid import uuid4

import json
import pandas as pd
import numpy as np
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.fmu_input import load_ensemble_set


class QualityCheckRealizations(WebvizPluginABC):
    """### Parameter correlation

Shows parameter correlation using a correlation matrix,
and scatter plot for any given pair of parameters.

* `ensembles`: Which ensembles in `shared_settings` to include in quality check.
* `status_file`: Name of json file with job status. Default: `status.json`
"""

    def __init__(
        self, app, ensembles, status_file="status.json",
    ):
        super().__init__()
        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.ensembles = ensembles
        self.status_file = status_file
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.color_by_labels = [
            "Same job in ensemble",
            "Slowest job in realization",
            "Slowest job in ensemble",
        ]
        self.uid = uuid4()
        self.status_df = make_status_df(self.ens_paths, self.status_file)
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": "Dashboard displaying state of realization jobs.",
            },
            {
                "id": self.ids("matrix"),
                "content": (
                    "Visualization of selected ensemble with chosen scaling. "
                    "Different options can be set in the menu above."
                ),
            },
            {
                "id": self.ids("ensemble"),
                "content": ("Display the realizations from the selected ensemble. "),
            },
            {
                "id": self.ids("relative"),
                "content": (
                    "Make the colorscale relative to runtime of the selected option."
                ),
            },
        ]

    @property
    def matrix_plot(self):
        return html.Div(
            style={"overflowX": "auto"},
            children=html.Div(
                children=wcc.Graph(
                    id=self.ids("matrix"), style={"width": "1px",}
                ),  # The 1px fixes a scrollbar /autosize bug for unknown reason
            ),
        )

    @property
    def control_div(self):
        return html.Div(
            style={
                "padding-top": 10,
                "display": "grid",
                "grid-template-columns": "1fr 3fr",
            },
            children=[
                html.Div(
                    children=[
                        html.Label("Set ensemble:", style={"font-weight": "bold"}),
                        html.Div(
                            children=[
                                dcc.Dropdown(
                                    id=self.ids("ensemble"),
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    clearable=False,
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Label(
                            "Color jobs relative to runtime of:",
                            style={"font-weight": "bold"},
                        ),
                        html.Div(
                            style={"padding-bottom": 20, "display": "grid",},
                            children=[
                                dcc.Dropdown(
                                    id=self.ids("relative"),
                                    options=[
                                        {"label": rel, "value": rel}
                                        for rel in self.color_by_labels
                                    ],
                                    value=self.color_by_labels[0],
                                    clearable=False,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(children=[self.control_div, self.matrix_plot,],)

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("matrix"), "figure"),
            [
                Input(self.ids("ensemble"), "value"),
                Input(self.ids("relative"), "value"),
            ],
        )
        def _update_matrix(ens, rel):
            """Update relative matrix
            Calls render_matrix to get the matrix for the selected input
            """
            return render_matrix(
                self.status_df[self.status_df["ENSEMBLE"] == ens],
                rel,
                theme=self.plotly_theme,
            )

    def add_webvizstore(self):
        return [
            (
                make_status_df,
                [{"ens_paths": self.ens_paths, "status_file": self.status_file}],
            )
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(status_df, rel, theme):
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
        "y": list(status_df["JOB_UNIQUE"]),
        "z": z,
        "zmin": 0,
        "zmax": 1,
        "text": list(status_df["HOVERINFO"]),
        "hoverinfo": "text",
        "colorscale": theme["layout"]["colorscale"]["sequential"],
    }
    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {"t": 50, "b": 50, "l": 50,},
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
                "tickvals": list(status_df["JOB_UNIQUE"]),
                "ticktext": list(status_df["JOB"]),
                "showgrid": False,
                "automargin": True,
                "autorange": "reversed",
            },
            "height": max(350, len(status_df["JOB_UNIQUE"].unique()) * 15),
            "width": max(400, len(status_df["REAL"].unique()) * 12 + 250),
        }
    )

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def make_status_df(ens_paths, status_file) -> pd.DataFrame:
    """Return pandas DataFrame of information from status.json files.
    *Finds status.json filepaths.
    *Loads data into pandas DataFrames.
    *Calculates runtimes and normalized runtimes.
    *Creates hoverinfo column to be used in visualization.
    """

    # Load ensembles and find filepaths to status.json-files.
    ens_set = load_ensemble_set(ens_paths)
    df = pd.concat(
        [
            ens_set[ens].find_files(status_file).assign(ENSEMBLE=ens)
            for ens in ens_set.ensemblenames
        ]
    )

    # Initial values
    status_dfs = []
    ens_dfs = []
    ens_max_job_runtime = 1
    ens = ""

    # Loop through identified filepaths.
    for index, row in df.iterrows():  # pylint: disable=unused-variable
        # Load each json-file to a DataFrame for the realization
        with open(row["FULLPATH"]) as fjson:
            status_dict = json.load(fjson)
        real_df = pd.DataFrame(status_dict["jobs"])

        # If new ensemble, calculate ensemble scaled runtimes
        # for previous ensemble and reset temporary ensemble data
        if ens != row["ENSEMBLE"]:
            if ens == "":
                ens = row["ENSEMBLE"]
            else:
                status_dfs.append(pd.concat(ens_dfs))
                status_dfs[-1]["JOB_SCALED_RUNTIME"] = status_dfs[-1][
                    "RUNTIME"
                ] / pd.concat([ens_max_job_runtime] * (len(ens_dfs)))
                status_dfs[-1]["ENS_SCALED_RUNTIME"] = status_dfs[-1][
                    "RUNTIME"
                ] / np.nanmax(ens_max_job_runtime)
                ens_max_job_runtime = 1
                ens_dfs = []
                ens = row["ENSEMBLE"]

        # Additional realization data into DataFrame
        real_df["RUNTIME"] = real_df["end_time"] - real_df["start_time"]
        real_df["REAL"] = row["REAL"]
        real_df["ENSEMBLE"] = row["ENSEMBLE"]
        real_df["REAL_SCALED_RUNTIME"] = real_df["RUNTIME"] / max(
            real_df["RUNTIME"].dropna()
        )
        real_df = real_df[
            ["ENSEMBLE", "REAL", "RUNTIME", "REAL_SCALED_RUNTIME", "name", "status"]
        ].rename(columns={"name": "JOB", "status": "STATUS"})
        real_df["JOB_UNIQUE"] = (
            real_df["JOB"]
            + list(map(str, range(0, len(real_df["JOB"]))))
            + "aEnasDkwLknmser"
        )  # Need unique job names to separate jobs in same realization with same name in json file

        # Update max runtime for jobs in ensemble
        ens_max_job_runtime = np.fmax(real_df["RUNTIME"], ens_max_job_runtime)

        # Append realization to ensemble data
        ens_dfs.append(real_df)

    # Add last ensemble
    status_dfs.append(pd.concat(ens_dfs))
    status_dfs[-1]["JOB_SCALED_RUNTIME"] = status_dfs[-1]["RUNTIME"] / pd.concat(
        [ens_max_job_runtime] * (len(ens_dfs))
    )
    status_dfs[-1]["ENS_SCALED_RUNTIME"] = status_dfs[-1]["RUNTIME"] / np.nanmax(
        ens_max_job_runtime
    )
    status_df = pd.concat(status_dfs, sort=False)

    # Create hoverinfo
    status_df["HOVERINFO"] = (
        "Real: "
        + status_df["REAL"].map(str)
        + "<br>"
        + "Job: "
        + status_df["JOB"].map(str)
        + "<br>"
        + "Runtime: "
        + status_df["RUNTIME"].map(str)
        + "<br>"
        + "Status: "
        + status_df["STATUS"]
    )

    return status_df
