from uuid import uuid4
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.containers import WebvizContainer
from webviz_subsurface.datainput import load_parameters
import plotly.express as px


class ParameterDistribution(WebvizContainer):
    """### ParameterDistribution

This container shows parameter distribution per ensemble as a histogram
with a marginal boxplot on top.

* `ensembles`: Which ensembles in `container_settings` to visualize.
"""

    def __init__(self, app, container_settings, ensembles):

        self.ensembles = tuple(
            (ens, container_settings["scratch_ensembles"][ens])
            for ens in ensembles
        )
        self.parameters = load_parameters(
            ensemble_paths=self.ensembles, ensemble_set_name="EnsembleSet"
        )
        self.parameter_columns = [
            col
            for col in list(self.parameters.columns)
            if col not in ["REAL", "ENSEMBLE"]
        ]
        self.uid = f"{uuid4()}"
        self.histogram_id = f"histogram-id-{self.uid}"
        self.pcol_id = f"pcol-id-{self.uid}"
        self.set_callbacks(app)

    def set_grid_layout(self, columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 4fr"),
            children=[
                html.Div(
                    [
                        html.H5("Select parameter"),
                        dcc.Dropdown(
                            id=self.pcol_id,
                            options=[
                                {"value": col, "label": col}
                                for col in self.parameter_columns
                            ],
                            value=self.parameter_columns[0],
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.H5(
                            style={"textAlign": "center"},
                            children="Parameter distribution",
                        ),
                        wcc.Graph(id=self.histogram_id),
                    ]
                ),
            ],
        )

    def set_callbacks(self, app):
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
                marginal="box",
            )

            return plot

    def add_webvizstore(self):
        return [
            (
                load_parameters,
                [
                    {
                        "ensemble_paths": self.ensembles,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ]
