from uuid import uuid4
import json
import numpy as np
import pandas as pd
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer


class TornadoPlot(WebvizContainer):
    """### TornadoPlot

This container visualizes a Tornado plot.

* `ensemble_paths`: Ensemble paths
* `ensemble_set_name`:  Name of ensemble set
* `reference`: Which sensitivity to use as reference.

"""

    def __init__(self, app, realizations, reference="rms_seed"):

        self.realizations = realizations
        self.senscases = list(self.realizations["SENSNAME"].unique())
        self.initial_reference = (
            reference if reference in self.senscases else self.senscases[0]
        )
        self._storage_id = f"{str(uuid4())}-tornado-data"
        self._reference_id = f"{str(uuid4())}-reference"
        self._graph_id = f"{str(uuid4())}-graph"
        self._scale_id = f"{str(uuid4())}-scale"
        self.set_callbacks(app)

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the tornado data"""
        return self._storage_id

    @property
    def layout(self):
        return html.Div(
            [
                dcc.Store(id=self.storage_id),
                html.Label("Reference"),
                dcc.Dropdown(
                    id=self._reference_id,
                    options=[{"label": r, "value": r} for r in self.senscases],
                    value=self.initial_reference,
                ),
                html.Label("Scale"),
                dcc.Dropdown(
                    id=self._scale_id,
                    options=[
                        {"label": r, "value": r} for r in ["Percentage", "Absolute"]
                    ],
                    value="Percentage",
                ),
                wcc.Graph(id=self._graph_id),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self._graph_id, "figure"),
            [
                Input(self._reference_id, "value"),
                Input(self._scale_id, "value"),
                Input(self.storage_id, "children"),
            ],
        )
        def _calc_tornado(reference, scale, data):
            data = json.loads(data)
            if not isinstance(data, dict):
                raise PreventUpdate
            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self.realizations.loc[
                self.realizations["ENSEMBLE"] == data["ENSEMBLE"]
            ]
            return tornado_plot(realizations, values, reference, scale)


def tornado_plot(realizations, data, reference="rms_seed", scale="Percentage"):

    if list(realizations["SENSCASE"].unique()) == [None]:
        return {}
    # Calculate average response value for reference sensitivity
    ref_avg = data.loc[
        data["REAL"].isin(
            realizations.loc[realizations["SENSNAME"] == reference]["REAL"]
        )
    ]["VALUE"].mean()

    arr = []
    # Group by sensitivity name/case and calculate average values for each case
    for (sens_name, sens_case), dframe in realizations.groupby(
        ["SENSNAME", "SENSCASE"]
    ):
        if sens_name == reference:
            continue
        values = data.loc[data["REAL"].isin(dframe["REAL"])]["VALUE"].mean()

        values_ref = values - ref_avg
        if scale == "Percentage":
            values_ref = (100 * (values_ref / ref_avg)) if ref_avg != 0 else 0
        arr.append(
            {
                "sensname": sens_name,
                "senscase": sens_case,
                "values": values,
                "values_ref": values_ref,
                "reals": list(dframe["REAL"]),
            }
        )

    arr2 = []
    # Group by sensitivity name and calculate low / high values
    for sensname, dframe in pd.DataFrame(arr).groupby(["sensname"]):
        low = dframe.loc[dframe["values_ref"].idxmin()]

        high = dframe.loc[dframe["values_ref"].idxmax()]

        arr2.append(
            {
                "low": low["values_ref"] if low["values_ref"] < 0 else 0,
                "low_label": low["senscase"],
                "true_low": low["values"],
                "low_reals": low["reals"] if low["values_ref"] < 0 else [],
                "name": sensname,
                "high": high["values_ref"] if high["values_ref"] > 0 else 0,
                "high_label": high["senscase"],
                "true_high": high["values"],
                "high_reals": high["reals"] if high["values_ref"] > 0 else [],
            }
        )
    df = pd.DataFrame(arr2).sort_values(by=["high"])

    # Return tornado data as Plotly figure
    return {
        "data": [
            dict(
                type="bar",
                y=df["name"],
                x=df["low"],
                name="low",
                hovertext=[
                    f"Case: {label}<br>True Value: {val:.2f}<br>Realizations:"
                    f"{min(reals) if reals else None}-{max(reals) if reals else None}"
                    for label, val, reals in zip(
                        df["low_label"], df["true_low"], df["low_reals"]
                    )
                ],
                hoverinfo="x+text",
                orientation="h",
                marker=dict(color="rgb(235, 0, 54)"),
            ),
            dict(
                type="bar",
                y=df["name"],
                x=df["high"],
                name="high",
                hovertext=[
                    f"Case: {label}<br>True Value: {val:.2f}<br>Realizations:"
                    f"{min(reals) if reals else None}-{max(reals) if reals else None}"
                    for label, val, reals in zip(
                        df["high_label"], df["true_high"], df["high_reals"]
                    )
                ],
                hoverinfo="x+text",
                orientation="h",
                marker=dict(color="rgb(36, 55, 70)"),
            ),
        ],
        "layout": {"barmode": "relative"},
    }
