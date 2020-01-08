from uuid import uuid4
import json
import pandas as pd

import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

import webviz_core_components as wcc
from webviz_config.common_cache import CACHE


class TornadoPlot:
    """### TornadoPlot

This private plugin visualizes a Tornado plot.
It is meant to be used as a component in other plugin, and is initialized
 with a dataframe of realizations with corresponding sensitivities,
but without the response values that are to be plotted.
Instead we registers a dcc.Store which will contain the response values.

To use:
1. Initialize an instance of this class in a plugin.
2. Add tornadoplot.layout to the plugin layout
3. Register a callback that writes a json dump to tornadoplot.storage_id
The format of the json dump must be:
{'ENSEMBLE': name of ensemble,
 'data': 2d array of realizations / response values}

Mouse events:
The current case at mouse cursor can be retrieved by registering a callback
that reads from  `tornadoplot.click_id` if `allow_click` has been specified at initialization.


* `realizations`: Dataframe of realizations with corresponding sensitivity cases
* `reference`: Which sensitivity to use as reference.
* `allow_click`: Registers a callback to store current data on mouse click

"""

    def __init__(
        self, app, realizations, reference="rms_seed", allow_click=False,
    ):

        self.realizations = realizations
        self.sensnames = list(self.realizations["SENSNAME"].unique())
        if self.sensnames == [None]:
            raise KeyError(
                "No sensitivity information found in ensemble. "
                "Containers utilizing tornadoplot can only be used for ensembles with "
                "one by one design matrix setup "
                "(SENSNAME and SENSCASE must be present in parameter file)."
            )
        self.initial_reference = (
            reference if reference in self.sensnames else self.sensnames[0]
        )
        self.allow_click = allow_click
        self.uid = uuid4()
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {"id": self.ids("tornado-graph"), "content": ("Shows tornado plot."),},
            {
                "id": self.ids("reference"),
                "content": (
                    "Set reference sensitivity for which to calculate tornado plot"
                ),
            },
            {
                "id": self.ids("scale"),
                "content": (
                    "Set tornadoplot scale to either percentage or absolute values"
                ),
            },
            {
                "id": self.ids("cut-by-ref"),
                "content": (
                    "Remove sensitivities smaller than the reference from the plot"
                ),
            },
            {
                "id": self.ids("reset"),
                "content": "Clears the currently selected sensitivity",
            },
        ]

    @property
    def storage_id(self):
        """The id of the dcc.Store component that holds the tornado data"""
        return self.ids("storage")

    @property
    def click_id(self):
        """The id of the dcc.Store component that holds click data"""
        return self.ids("click-store")

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
            [
                html.Div(
                    style={"marginLeft": "20%"},
                    children=[
                        html.Label(
                            "Tornado Plot",
                            style={"textAlign": "center", "font-weight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[html.Label("Reference:"), html.Label("Scale:"),],
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    id=self.ids("reference"),
                                    options=[
                                        {"label": r, "value": r} for r in self.sensnames
                                    ],
                                    value=self.initial_reference,
                                    clearable=False,
                                ),
                                dcc.Dropdown(
                                    id=self.ids("scale"),
                                    options=[
                                        {"label": r, "value": r}
                                        for r in ["Percentage", "Absolute"]
                                    ],
                                    value="Percentage",
                                    clearable=False,
                                ),
                            ],
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                html.Label(
                                    style={"marginTop": "10px"},
                                    children="Cut by reference:",
                                )
                            ],
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                dcc.RadioItems(
                                    labelStyle={"display": "inline-block"},
                                    id=self.ids("cut-by-ref"),
                                    options=[
                                        {"label": "Off", "value": False},
                                        {"label": "On", "value": True},
                                    ],
                                    value=False,
                                ),
                                html.Button(
                                    style={
                                        "position": "relative",
                                        "top": "-50%",
                                        "fontSize": "10px",
                                    },
                                    id=self.ids("reset"),
                                    children="Clear selected",
                                ),
                            ],
                        ),
                        wcc.Graph(
                            id=self.ids("tornado-graph"),
                            config={"displayModeBar": False},
                        ),
                        dcc.Store(id=self.ids("storage")),
                        dcc.Store(id=self.ids("click-store")),
                    ],
                )
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("tornado-graph"), "figure"),
            [
                Input(self.ids("reference"), "value"),
                Input(self.ids("scale"), "value"),
                Input(self.ids("cut-by-ref"), "value"),
                Input(self.ids("storage"), "children"),
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
                return tornado_plot(
                    realizations,
                    values,
                    plotly_theme=self.plotly_theme,
                    reference=reference,
                    scale=scale,
                    cutbyref=cutbyref,
                )
            except KeyError:
                return {}

        if self.allow_click:

            @app.callback(
                Output(self.ids("click-store"), "children"),
                [
                    Input(self.ids("tornado-graph"), "clickData"),
                    Input(self.ids("reset"), "n_clicks"),
                ],
            )
            def _save_click_data(data, nclicks):
                if not dash.callback_context.triggered:
                    raise PreventUpdate

                ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

                if ctx == self.ids("reset") and nclicks:

                    return json.dumps(
                        {"real_low": [], "real_high": [], "sens_name": None,}
                    )
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
    realizations,
    data,
    plotly_theme,
    reference="rms_seed",
    scale="Percentage",
    cutbyref=True,
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

    plot_data = [
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
        ),
    ]
    layout = {}
    layout.update(plotly_theme["layout"])
    layout.update(
        {
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
                "title": None,
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
        }
    )
    return {"data": plot_data, "layout": layout}
