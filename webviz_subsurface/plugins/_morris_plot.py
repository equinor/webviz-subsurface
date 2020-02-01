from uuid import uuid4
from pathlib import Path
import pandas as pd

import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_subsurface_components import Morris
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC


class MorrisPlot(WebvizPluginABC):
    """### Morris

Renders a visualization of the Morris sampling method.
The Morris method can be used to screen parameters for how they
influence model response, both individually and through interaction
effect with other parameters.

* `csv_file`: Input data
* `title`: Optional title for the plugin.
"""

    def __init__(self, app, csv_file: Path):

        super().__init__()

        self.graph_id = "graph-{}".format(uuid4())
        self.vector_id = "vector-{}".format(uuid4())
        self.csv_file = csv_file
        self.data = read_csv(self.csv_file)
        self.vector_names = self.data["name"].unique()
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div(
            [
                html.Label("Vector", style={"font-size": "2rem"}),
                dcc.Dropdown(
                    id=self.vector_id,
                    clearable=False,
                    options=[{"label": i, "value": i} for i in list(self.vector_names)],
                    value=self.vector_names[0],
                ),
                Morris(id=self.graph_id),
            ]
        )

    def add_webvizstore(self):
        return [(read_csv, [{"csv_file": self.csv_file}])]

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.graph_id, "output"),
                Output(self.graph_id, "parameter"),
                Output(self.graph_id, "parameters"),
            ],
            [Input(self.vector_id, "value")],
        )
        def _update_plot(vector):
            df = self.data[self.data["name"] == vector]
            df = df.sort_values("time")
            output = (
                df[["mean", "max", "min", "time"]]
                .drop_duplicates()
                .to_dict(orient="records")
            )
            parameters = []

            for name in self.data["name"].unique():
                if name != vector:
                    name_df = self.data[self.data["name"] == name]
                    parameters.append(
                        {
                            "main": list(name_df["morris_main"]),
                            "name": str(name),
                            "interactions": list(name_df["morris_interaction"]),
                        }
                    )
            return output, vector, parameters


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file)
