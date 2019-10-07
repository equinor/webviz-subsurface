from uuid import uuid4
import json
import pandas as pd

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

from webviz_config.common_cache import CACHE
import webviz_core_components as wcc


class TornadoPlot:
    """### TornadoPlot

This private container visualizes a Tornado plot.
It is meant to be used as a component in other containers.
The container is initialized with a dataframe of realizations with corresponding sensitivities,
but without the response values that are to be plotted.
Instead the container registers a dcc.Store which will contain the response values.

To use:
1. Initialize an instance of this class in a container
2. Add tornadoplot.layout to the container layout
3. Register a callback that writes a json dump to tornadoplot.storage_id
The format of the json dump must be:
{'ENSEMBLE': name of ensemble,
 'data': 2d array of realizations / response values}

Mouse events:
The current case at mouse cursor can be retrieved by registering a callback
that reads from `tornadoplot.hover_id` or `tornadoplot.click_id` if `allow_hover`
or `allow_click` has been specified at initialization.


* `realizations`: Dataframe of realizations with corresponding sensitivity cases
* `reference`: Which sensitivity to use as reference.
* `allow_hover`: Registers a callback to store current data on mouse hover
* `allow_click`: Registers a callback to store current data on mouse click

"""

    def __init__(
        self,
        app,
        realizations,
        reference="rms_seed",
        allow_hover=False,
        allow_click=False,
    ):

        self.realizations = realizations
        self.senscases = list(self.realizations["SENSNAME"].unique())
        self.initial_reference = (
            reference if reference in self.senscases else self.senscases[0]
        )
        self.allow_hover = allow_hover
        self.allow_click = allow_click
        self._storage_id = f"{str(uuid4())}-tornado-data"
        self._reference_id = f"{str(uuid4())}-reference"
        self._graph_id = f"{str(uuid4())}-graph"
        self._hover_id = f"{str(uuid4())}-hover"
        self._click_id = f"{str(uuid4())}-click"
        self._scale_id = f"{str(uuid4())}-scale"
        self._cut_by_ref_id = f"{str(uuid4())}-cutref"
        self.set_callbacks(app)

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the tornado data"""
        return self._storage_id

    @property
    def hover_id(self):
        """The id of the dcc.Store component that holds hover data"""
        return self._hover_id

    @property
    def click_id(self):
        """The id of the dcc.Store component that holds click data"""
        return self._click_id

    @property
    def layout(self):
        return html.Div(
            [
                dcc.Store(id=self.storage_id),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr"},
                    children=[
                        html.Label("Reference"),
                        html.Label("Scale"),
                        html.Label("Cut by reference"),
                    ],
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr"},
                    children=[
                        dcc.Dropdown(
                            id=self._reference_id,
                            options=[{"label": r, "value": r} for r in self.senscases],
                            value=self.initial_reference,
                            clearable=False,
                        ),
                        dcc.Dropdown(
                            id=self._scale_id,
                            options=[
                                {"label": r, "value": r}
                                for r in ["Percentage", "Absolute"]
                            ],
                            value="Percentage",
                            clearable=False,
                        ),
                        dcc.RadioItems(
                            labelStyle={"display": "inline-block"},
                            id=self._cut_by_ref_id,
                            options=[
                                {"label": "Off", "value": False},
                                {"label": "On", "value": True},
                            ],
                            value=False,
                        ),
                    ],
                ),
                wcc.Graph(id=self._graph_id, config={"displayModeBar": False}),
                dcc.Store(id=self.hover_id),
                dcc.Store(id=self.click_id),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self._graph_id, "figure"),
            [
                Input(self._reference_id, "value"),
                Input(self._scale_id, "value"),
                Input(self._cut_by_ref_id, "value"),
                Input(self.storage_id, "children"),
            ],
        )
        def _calc_tornado(reference, scale, cutbyref, data):
            if not data:
                raise PreventUpdate
            data = json.loads(data)
            if not isinstance(data, dict):
                raise PreventUpdate
            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self.realizations.loc[
                self.realizations["ENSEMBLE"] == data["ENSEMBLE"]
            ]
            try:
                return tornado_plot(realizations, values, reference, scale, cutbyref)
            except KeyError:
                return {}

        if self.allow_hover:

            @app.callback(
                Output(self.hover_id, "children"), [Input(self._graph_id, "hoverData")]
            )
            def _save_hover_data(data):
                try:
                    real_low = data["points"][0]["customdata"]
                    real_high = data["points"][1]["customdata"]
                    sens_name = data["points"][0]["y"]
                    return json.dumps(
                        {
                            "real_low": real_low,
                            "real_high": real_high,
                            "sens_name": sens_name,
                        }
                    )
                except TypeError:
                    raise PreventUpdate

        if self.allow_click:

            @app.callback(
                Output(self.click_id, "children"), [Input(self._graph_id, "clickData")]
            )
            def _save_hover_data(data):
                try:
                    real_low = data["points"][0]["customdata"]
                    real_high = data["points"][1]["customdata"]
                    sens_name = data["points"][0]["y"]
                    return json.dumps(
                        {
                            "real_low": real_low,
                            "real_high": real_high,
                            "sens_name": sens_name,
                        }
                    )
                except TypeError:
                    raise PreventUpdate


def scale_to_ref(value, ref, scale):
    value_ref = value - ref
    if scale == "Percentage":
        value_ref = (100 * (value_ref / ref)) if ref != 0 else 0
    return value_ref


def sort_by_max(tornadotable):
    """ Sorts table based on max(abs('low', 'high')) """
    tornadotable["max"] = (
        tornadotable[["low", "high"]]
        .apply(lambda x: max(x.min(), x.max(), key=abs), axis=1)
        .abs()
    )
    df_sorted = tornadotable.sort_values("max", ascending=True)
    df_sorted.drop(["max"], axis=1, inplace=True)
    return df_sorted


def cut_by_ref(tornadotable, refname):
    """ Removes sensitivities smaller than reference sensitivity from table """
    maskref = tornadotable.sensname == refname
    reflow = tornadotable[maskref].low.abs()
    refhigh = tornadotable[maskref].high.abs()
    refmax = max(float(reflow), float(refhigh))
    dfr_filtered = tornadotable.loc[
        (tornadotable["sensname"] == refname)
        | (
            (tornadotable["low"].abs() >= refmax)
            | (tornadotable["high"].abs() >= refmax)
        )
    ]
    return dfr_filtered


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def tornado_plot(
    realizations, data, reference="rms_seed", scale="Percentage", cutbyref=True
):  # pylint: disable=too-many-locals

    # Raise key error if no senscases, i.e. the ensemble has no design matrix
    if list(realizations["SENSCASE"].unique()) == [None]:
        raise KeyError

    # Calculate average response value for reference sensitivity
    ref_avg = data.loc[
        data["REAL"].isin(
            realizations.loc[realizations["SENSNAME"] == reference]["REAL"]
        )
    ]["VALUE"].mean()

    # Group by sensitivity name/case and calculate average values for each case
    arr = []
    for sens_name, sens_name_df in realizations.groupby(["SENSNAME"]):
        # Excluding the reference case as well as any cases named `ref`
        # `ref` is used as `SENSNAME`, typically for a single realization only,
        # when no seed uncertainty is used
        if sens_name == "ref":
            continue

        # If `SENSTYPE` is scalar grab the mean for each `SENSCASE`
        if sens_name_df["SENSTYPE"].all() == "scalar":
            for sens_case, sens_case_df in sens_name_df.groupby(["SENSCASE"]):
                values = data.loc[data["REAL"].isin(sens_case_df["REAL"])][
                    "VALUE"
                ].mean()

                arr.append(
                    {
                        "sensname": sens_name,
                        "senscase": sens_case,
                        "values": values,
                        "values_ref": scale_to_ref(values, ref_avg, scale),
                        "reals": list(sens_case_df["REAL"]),
                    }
                )
        # If `SENSTYPE` is monte carlo get p10, p90
        elif sens_name_df["SENSTYPE"].all() == "mc":
            # Get data for relevant realizations
            case_df = data.loc[data["REAL"].isin(sens_name_df["REAL"])]

            # Calculate p90(low) and p10(high)
            p90 = case_df["VALUE"].quantile(0.10)
            p10 = case_df["VALUE"].quantile(0.90)

            # Extract list of realizations with values less then reference avg (low)
            low_reals = list(case_df.loc[case_df["VALUE"] <= ref_avg]["REAL"])

            # Extract list of realizations with values higher then reference avg (high)
            high_reals = list(case_df.loc[case_df["VALUE"] > ref_avg]["REAL"])

            arr.append(
                {
                    "sensname": sens_name,
                    "senscase": "p90",
                    "values": p90,
                    "values_ref": scale_to_ref(p90, ref_avg, scale),
                    "reals": low_reals,
                }
            )
            arr.append(
                {
                    "sensname": sens_name,
                    "senscase": "p10",
                    "values": p10,
                    "values_ref": scale_to_ref(p10, ref_avg, scale),
                    "reals": high_reals,
                }
            )
        else:
            raise ValueError(
                f"Sensitivities should be either 'scalar'or 'mc'. \
                Sensitivity: '{sens_name}' is neither."
            )

    # Group by sensitivity name and calculate low / high values
    arr2 = []
    for sensname, sens_name_df in pd.DataFrame(arr).groupby(["sensname"]):
        low = sens_name_df.loc[sens_name_df["values_ref"].idxmin()]
        high = sens_name_df.loc[sens_name_df["values_ref"].idxmax()]
        arr2.append(
            {
                "low": low["values_ref"] if low["values_ref"] < 0 else 0,
                "low_label": low["senscase"],
                "true_low": low["values"],
                "low_reals": low["reals"],
                "sensname": sensname,
                "high": high["values_ref"] if high["values_ref"] > 0 else 0,
                "high_label": high["senscase"],
                "true_high": high["values"],
                "high_reals": high["reals"],
            }
        )

    df = pd.DataFrame(arr2)

    # Drops sensitivities smaller than reference if specified
    if cutbyref and df["sensname"].str.contains(reference).any():
        df = cut_by_ref(df, reference)

    df = sort_by_max(df)
    # Return tornado data as Plotly figure

    return {
        "data": [
            dict(
                type="bar",
                y=df["sensname"],
                x=df["low"],
                name="low",
                customdata=df["low_reals"],
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
                y=df["sensname"],
                x=df["high"],
                name="high",
                customdata=df["high_reals"],
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
        "layout": {
            "barmode": "relative",
            "margin": {"l": 50, "r": 50, "b": 20, "t": 50},
            "xaxis": {
                "title": scale,
                "autorange": True,
                "showgrid": False,
                "zeroline": False,
                "showline": True,
                "automargin": True,
            },
            "yaxis": {
                "autorange": True,
                "showgrid": False,
                "zeroline": False,
                "showline": False,
                "automargin": True,
            },
            "showlegend": False,
            "annotations": [
                {
                    "x": 0,
                    "y": len(list(df["low"])),
                    "xref": "x",
                    "yref": "y",
                    "text": f"Reference avg: {ref_avg:.2f}",
                    "showarrow": True,
                    "align": "center",
                    "arrowhead": 2,
                    "arrowsize": 1,
                    "arrowwidth": 1,
                    "arrowcolor": "#636363",
                    "ax": 20,
                    "ay": -25,
                }
            ],
        },
    }
