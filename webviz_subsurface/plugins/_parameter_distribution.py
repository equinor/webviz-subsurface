from uuid import uuid4
from pathlib import Path

import pandas as pd
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_subsurface_components as wsc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._datainput.fmu_input import load_parameters


class ParameterDistribution(WebvizPluginABC):
    """### ParameterDistribution

Shows parameter distributions for FMU ensembles.
Parameters are visualized per ensemble as a histogram, and as a boxplot showing
the parameter ranges for each ensemble.
Input can be given either as an aggregated csv files with parameter information
or as an ensemble name defined in `shared_settings`.

* `csvfile`: Aggregated csvfile with 'REAL', 'ENSEMBLE' and parameter columns
* `ensembles`: Which ensembles in `shared_settings` to visualize.
"""

    def __init__(self, app, csvfile: Path = None, ensembles: list = None):

        super().__init__()

        self.csvfile = csvfile if csvfile else None

        if csvfile and ensembles:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles".'
            )
        if csvfile:
            self.parameters = read_csv(csvfile)
        elif ensembles:
            self.ensembles = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
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
        self.uid = uuid4()
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": ("Dashboard displaying distribution of input parameters"),
            },
            {
                "id": self.ids("graph"),
                "content": (
                    "Visualization of currently selected parameter as histogram "
                    "series and distribution range per ensemble."
                ),
            },
            {
                "id": self.ids("parameter"),
                "content": (
                    "Select visualized parameter by selecting or searching the list."
                ),
            },
        ]

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
            id=self.ids("layout"),
            children=[
                html.Span("Parameter distribution:", style={"font-weight": "bold"}),
                html.Div(
                    style=self.set_grid_layout("8fr 1fr 2fr"),
                    children=[
                        dcc.Dropdown(
                            id=self.ids("parameter"),
                            options=[
                                {"value": col, "label": col}
                                for col in self.parameter_columns
                            ],
                            value=self.parameter_columns[0],
                            clearable=False,
                        ),
                        self.make_buttons(self.ids("prev-btn"), self.ids("next-btn")),
                    ],
                ),
                wsc.PriorPosteriorDistribution(id=self.ids("graph")),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("parameter"), "value"),
            [
                Input(self.ids("prev-btn"), "n_clicks"),
                Input(self.ids("next-btn"), "n_clicks"),
            ],
            [State(self.ids("parameter"), "value")],
        )
        def _set_parameter_from_btn(_prev_click, _next_click, column):

            ctx = dash.callback_context.triggered
            if not ctx:
                raise PreventUpdate
            callback = ctx[0]["prop_id"]
            if callback == f"{self.ids('prev-btn')}.n_clicks":
                column = prev_value(column, self.parameter_columns)
            elif callback == f"{self.ids('next-btn')}.n_clicks":
                column = next_value(column, self.parameter_columns)
            return column

        @app.callback(
            Output(self.ids("graph"), "data"), [Input(self.ids("parameter"), "value")]
        )
        def _set_parameter(column):
            param = self.parameters[[column, "REAL", "ENSEMBLE"]]

            ensembles = param["ENSEMBLE"].unique().tolist()

            iterations = []
            values = []
            labels = []

            for ensemble in ensembles:
                df = param[param["ENSEMBLE"] == ensemble]
                iterations.append(ensemble)
                values.append(df[column].tolist())
                labels.append([f"Realization {real}" for real in df["REAL"].tolist()])

            return {"iterations": iterations, "values": values, "labels": labels}

    def add_webvizstore(self):
        return [
            (read_csv, [{"csv_file": self.csvfile}])
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
