from uuid import uuid4
from pathlib import Path

import pandas as pd
import plotly.express as px
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizContainerABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from ..datainput import load_parameters


class ParameterDistribution(WebvizContainerABC):
    """### ParameterDistribution

This container shows parameter distributions for FMU ensembles.
Parameters are visualized per ensemble as a histogram, and as a boxplot showing
the parameter ranges for each ensemble.
Input can be given either as an aggregated csv files with parameter information
or as an ensemble name defined in `container_settings`.

* `csvfile`: Aggregated csvfile with 'REAL', 'ENSEMBLE' and parameter columns
* `ensembles`: Which ensembles in `container_settings` to visualize.
"""

    def __init__(
        self, app, container_settings, csvfile: Path = None, ensembles: list = None
    ):

        self.csvfile = csvfile if csvfile else None

        if csvfile and ensembles:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles".'
            )
        if csvfile:
            self.parameters = read_csv(csvfile)
        elif ensembles:
            self.ensembles = tuple(
                (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
            )
            self.parameters = load_parameters(
                ensemble_paths=self.ensembles, ensemble_set_name="EnsembleSet"
            )
        else:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles".'
            )

        self.parameter_columns = [
            col
            for col in list(self.parameters.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]
        self.uid = f"{uuid4()}"
        self.histogram_id = f"histogram-id-{self.uid}"
        self.prev_btn_id = f"prev-btn-id-{self.uid}"
        self.next_btn_id = f"next-btn-id-{self.uid}"
        self.pcol_id = f"pcol-id-{self.uid}"
        self.set_callbacks(app)

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def make_buttons(self, prev_id, next_id):
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(id=prev_id, children="<="),
                html.Button(id=next_id, children="=>"),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            [
                html.H5("Select parameter distribution"),
                html.Div(
                    style=self.set_grid_layout("8fr 1fr 2fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.pcol_id,
                            options=[
                                {"value": col, "label": col}
                                for col in self.parameter_columns
                            ],
                            value=self.parameter_columns[0],
                            clearable=False,
                        ),
                        self.make_buttons(self.prev_btn_id, self.next_btn_id),
                    ],
                ),
                wcc.Graph(id=self.histogram_id),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.pcol_id, "value"),
            [Input(self.prev_btn_id, "n_clicks"), Input(self.next_btn_id, "n_clicks")],
            [State(self.pcol_id, "value")],
        )
        def _set_parameter_from_btn(_prev_click, _next_click, column):

            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            callback = ctx[0]["prop_id"]
            if callback == f"{self.prev_btn_id}.n_clicks":
                column = prev_value(column, self.parameter_columns)
            elif callback == f"{self.next_btn_id}.n_clicks":
                column = next_value(column, self.parameter_columns)
            return column

        @app.callback(
            Output(self.histogram_id, "figure"), [Input(self.pcol_id, "value")]
        )
        def _set_parameter(column):
            param = self.parameters[[column, "REAL", "ENSEMBLE"]]

            plot = px.histogram(
                param,
                x=column,
                y="REAL",
                color="ENSEMBLE",
                hover_data=["REAL"],
                barmode="overlay",
                nbins=10,
                range_x=[param[column].min(), param[column].max()],
                marginal="box",
            ).for_each_trace(lambda t: t.update(name=t.name.replace("ENSEMBLE=", "")))

            return plot

    def add_webvizstore(self):
        return [
            (read_csv, [{"csv_file": self.csvfile,}],)
            if self.csvfile
            else (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ensembles,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ]


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
    except ValueError:
        index = None
    if index > 0:
        return options[index - 1]
    return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
    except ValueError:
        index = None
    if index < len(options) - 1:
        return options[index + 1]
    return current_value


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)
