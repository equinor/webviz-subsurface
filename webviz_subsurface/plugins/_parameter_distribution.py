from pathlib import Path
from typing import Callable, Dict, List, Tuple
from uuid import uuid4

import pandas as pd
import webviz_subsurface_components as wsc
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._datainput.fmu_input import load_parameters


class ParameterDistribution(WebvizPluginABC):
    """Visualizes parameter distributions for FMU ensembles.

Parameters are visualized either as histograms, showing parameter ranges
and distributions for each ensemble.

Input can be given either as an aggregated `csv` file with parameter information,
or as ensemble name(s) defined in `shared_settings`.

---

**Using aggregated data**
* **`csvfile`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns. \
 (absolute path or relative to config file).

**Reading data from ensembles**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.

---
Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`, using the `fmu-ensemble` library.

When using an aggregated `csvfile`, you need to have the columns `REAL`, `ENSEMBLE`
and the parameter columns.
"""

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile: Path = None,
        ensembles: list = None,
    ):

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
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.parameters = load_parameters(
                ensemble_paths=self.ensembles, ensemble_set_name="EnsembleSet"
            )
        else:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles".'
            )

        self.parameter_columns: List[str] = [
            col
            for col in list(self.parameters.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]
        self.uid = uuid4()
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self) -> List[dict]:
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
    def set_grid_layout(columns: str) -> Dict[str, str]:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def make_buttons(self, prev_id: str, next_id: str) -> html.Div:
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(
                    id=prev_id,
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    children="⬅",
                ),
                html.Button(
                    id=next_id,
                    style={
                        "fontSize": "2rem",
                        "paddingLeft": "5px",
                        "paddingRight": "5px",
                    },
                    children="➡",
                ),
            ],
        )

    @property
    def layout(self) -> html.Div:
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
                            persistence=True,
                            persistence_type="session",
                        ),
                        self.make_buttons(self.ids("prev-btn"), self.ids("next-btn")),
                    ],
                ),
                wsc.PriorPosteriorDistribution(id=self.ids("graph")),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.ids("parameter"), "value"),
            [
                Input(self.ids("prev-btn"), "n_clicks"),
                Input(self.ids("next-btn"), "n_clicks"),
            ],
            [State(self.ids("parameter"), "value")],
        )
        def _set_parameter_from_btn(
            _prev_click: int, _next_click: int, column: str
        ) -> str:

            ctx = callback_context.triggered
            if ctx is None:
                raise PreventUpdate
            callback = ctx[0]["prop_id"]
            if callback == f"{self.ids('prev-btn')}.n_clicks":
                column = prev_value(column, self.parameter_columns)
            elif callback == f"{self.ids('next-btn')}.n_clicks":
                column = next_value(column, self.parameter_columns)
            else:
                column = self.parameter_columns[0]
            return column

        @app.callback(
            Output(self.ids("graph"), "data"), [Input(self.ids("parameter"), "value")]
        )
        def _set_parameter(column: str) -> dict:
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

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
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


def prev_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value: str, options: List[str]) -> str:
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]
    except ValueError:
        return current_value


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)
