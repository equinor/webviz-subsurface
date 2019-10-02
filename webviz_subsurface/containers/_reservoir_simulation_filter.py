from uuid import uuid4
import json

import numpy as np
import pandas as pd


from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
from dash_table import DataTable

import webviz_core_components as wcc
from webviz_config import WebvizContainerABC
from webviz_config.common_cache import CACHE
from webviz_subsurface.private_containers._parameter_filter import ParameterFilter

from ..datainput import load_parameters, load_smry


class ReservoirSimulationParameterFilter(WebvizContainerABC):
    """### Visualizes reservoir simulation time series with a an option to filter
    input parameters

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `column_keys`: List of vectors to extract. If not given, all vectors
                 from the simulations will be extracted. Wild card asterisk *
                 can be used.
* `initial_vector`: Initial vector to display
* `sampling`: Time separation between extracted values. Can be e.g. `monthly`
              or `yearly`.
"""

    ENSEMBLE_COLUMNS = [
        "REAL",
        "ENSEMBLE",
        "DATE",
        "SENSCASE",
        "SENSNAME",
        "SENSTYPE",
        "RUNPATH",
    ]

    TABLE_STATISTICS = ["Date", "Mean", "Stddev", "Minimum", "P90", "P10", "Maximum"]

    def __init__(
        self,
        app,
        container_settings,
        ensembles,
        column_keys=None,
        initial_vector=None,
        sampling: str = "monthly",
    ):

        self.time_index = sampling
        self.column_keys = tuple(column_keys) if column_keys else None
        self.ens_paths = tuple(
            (ensemble, container_settings["scratch_ensembles"][ensemble])
            for ensemble in ensembles
        )
        # Extract realizations and sensitivity information
        parameters = load_parameters(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )
        smry = load_smry(
            ensemble_paths=self.ens_paths,
            ensemble_set_name="EnsembleSet",
            time_index=self.time_index,
            column_keys=self.column_keys,
        )

        self.data = pd.merge(smry, parameters, on=["ENSEMBLE", "REAL"])
        self.smry_cols = [
            c
            for c in self.data.columns
            if c not in ReservoirSimulationParameterFilter.ENSEMBLE_COLUMNS
        ]
        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self.smry_cols
            else self.smry_cols[0]
        )
        self.parameterfilter = ParameterFilter(app, parameters)

        self.make_uuids()

        self.set_callbacks(app)

    def make_uuids(self):
        uuid = f"{uuid4()}"
        self.smry_col_id = f"smry-col-{uuid}"
        self.date_id = f"date-{uuid}"
        self.date_label = f"date-label{uuid}"
        self.ensemble_id = f"ensemble-{uuid}"
        self.table_id = f"table-{uuid}"
        self.graph_id = f"graph-{uuid}"
        self.graph_wrapper_id = f"graph-wrapper-{uuid}"

    @property
    def ensemble_selector(self):
        """Dropdown to select ensemble"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=[
                html.Label("Ensemble"),
                dcc.Dropdown(
                    id=self.ensemble_id,
                    options=[
                        {"label": i, "value": i}
                        for i in list(self.data["ENSEMBLE"].unique())
                    ],
                    clearable=False,
                    value=list(self.data["ENSEMBLE"])[0],
                ),
            ],
        )

    @property
    def smry_selector(self):
        """Dropdown to select ensemble"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=[
                html.Label("Vector"),
                dcc.Dropdown(
                    id=self.smry_col_id,
                    options=[{"label": i, "value": i} for i in self.smry_cols],
                    clearable=False,
                    value=self.initial_vector,
                ),
            ],
        )

    def add_webvizstore(self):
        return [
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
            ),
            (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            ),
        ]

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("3fr 1fr"),
            children=[
                html.Div(
                    [
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr 1fr"),
                            children=[
                                self.ensemble_selector,
                                self.smry_selector,
                                html.Label(id=self.date_label),
                            ],
                        ),
                        html.Div(
                            [
                                html.Div(
                                    id=self.graph_wrapper_id,
                                    style={"height": "450px"},
                                    children=wcc.Graph(id=self.graph_id),
                                ),
                                DataTable(
                                    id=self.table_id,
                                    sort_action="native",
                                    filter_action="native",
                                    page_action="native",
                                    page_size=10,
                                    columns=[
                                        {"name": i, "id": i}
                                        for i in ReservoirSimulationParameterFilter.TABLE_STATISTICS
                                    ],
                                ),
                            ]
                        ),
                    ]
                ),
                self.parameterfilter.layout,
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [Output(self.graph_id, "figure"), Output(self.table_id, "data")],
            [
                Input(self.ensemble_id, "value"),
                Input(self.smry_col_id, "value"),
                Input(self.parameterfilter.storage_id, "children"),
            ],
        )
        def _render_lines(ensemble, vector, reals):
            """Callback to update graph, and tornado"""

            reals = json.loads(reals) if reals else []
            print(reals)

            # Filter dataframe based on dropdown choices
            data = filter_ensemble(self.data, ensemble, vector)

            traces = [
                {
                    "type": "line",
                    "hoverinfo": "skip",
                    "x": df["DATE"],
                    "y": df[vector],
                    "customdata": r,
                    "marker": {"color": "rgb(235, 0, 54)"}
                    if r in reals
                    else {"color": "grey"},
                    "opacity": 1 if r in reals else 0.1,
                }
                for r, df in data.groupby(["REAL"])
            ]
            traces[0]["hoverinfo"] = "x"
            figure = {"data": traces, "layout": {"showlegend": False}}
            data = data.loc[data["REAL"].isin(reals)] if reals else data
            tabledata = calculate_table_rows(data, vector)
            return figure, tabledata


def calculate_table_rows(df, vector):
    table = []
    for date, dframe in df.groupby(["DATE"]):
        values = dframe[vector]
        try:
            table.append(
                {
                    "Date": str(date),
                    "Minimum": f"{values.min():.2e}",
                    "Maximum": f"{values.max():.2e}",
                    "Mean": f"{values.mean():.2e}",
                    "Stddev": f"{values.std():.2e}",
                    "P10": f"{np.percentile(values, 90):.2e}",
                    "P90": f"{np.percentile(values, 10):.2e}",
                }
            )
        except KeyError:
            pass
    return table


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_ensemble(data, ensemble, vector):
    return data.loc[data["ENSEMBLE"] == ensemble][["DATE", "REAL", vector]]
