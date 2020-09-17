from uuid import uuid4
import json
from typing import List, Optional

import pandas as pd
import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE

from .._abbreviations.number_formatting import si_prefixed


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
    The format of the json dump must be ('ENSEMBLE' and 'data' are mandatory, the others optional):
    {'ENSEMBLE': name of ensemble,
     'data': 2d array of realizations / response values
     'number_format' (str): Format of the numeric part based on the Python Format Specification
      Mini-Language e.g. '#.3g' for 3 significant digits, '.2f' for two decimals, or '.0f' for no
      decimals.
     'unit' (str): String to append at the end as a unit.
     'spaced' (bool): Include a space between last numerical digit and SI-prefix.
     'locked_si_prefix' (str or int): Lock the SI prefix to either a string (e.g. 'm' (milli) or 'M'
      (mega)), or an integer which is the base 10 exponent (e.g. 3 for kilo, -3 for milli).
    }

    Mouse events:
    The current case at mouse cursor can be retrieved by registering a callback
    that reads from  `tornadoplot.click_id` if `allow_click` has been specified at initialization.


    * `realizations`: Dataframe of realizations with corresponding sensitivity cases
    * `reference`: Which sensitivity to use as reference.
    * `allow_click`: Registers a callback to store current data on mouse click
    """

    def __init__(
        self,
        app,
        realizations,
        reference="rms_seed",
        allow_click=False,
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
            {
                "id": self.ids("tornado-graph"),
                "content": ("Shows tornado plot."),
            },
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

    @property
    def high_low_storage_id(self):
        """The id of the dcc.Store component that holds click data"""
        return self.ids("high-low-storage")

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
                    style={"marginLeft": "10px"},
                    children=[
                        html.Label(
                            "Tornado Plot",
                            style={"textAlign": "center", "font-weight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                html.Label("Reference:"),
                                html.Label("Scale:"),
                            ],
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
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("scale"),
                                    options=[
                                        {"label": r, "value": r}
                                        for r in ["Percentage", "Absolute"]
                                    ],
                                    value="Percentage",
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                        ),
                        dcc.Checklist(
                            id=self.ids("cut-by-ref"),
                            options=[
                                {
                                    "label": "Cut by reference",
                                    "value": "Cut by reference",
                                },
                            ],
                            value=[],
                            persistence=True,
                            persistence_type="session",
                        ),
                        html.Details(
                            open=False,
                            children=[
                                html.Summary("Filter"),
                                wcc.Select(
                                    id=self.ids("sens_filter"),
                                    options=[
                                        {"label": i, "value": i} for i in self.sensnames
                                    ],
                                    value=self.sensnames,
                                    multi=True,
                                    size=min(10, len(self.sensnames)),
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
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
                        wcc.Graph(
                            id=self.ids("tornado-graph"),
                            config={"displayModeBar": False},
                        ),
                        dcc.Store(id=self.ids("storage"), storage_type="session"),
                        dcc.Store(id=self.ids("click-store"), storage_type="session"),
                        dcc.Store(
                            id=self.ids("high-low-storage"), storage_type="session"
                        ),
                    ],
                )
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("tornado-graph"), "figure"),
                Output(self.ids("high-low-storage"), "data"),
            ],
            [
                Input(self.ids("reference"), "value"),
                Input(self.ids("scale"), "value"),
                Input(self.ids("cut-by-ref"), "value"),
                Input(self.ids("storage"), "data"),
                Input(self.ids("sens_filter"), "value"),
            ],
        )
        def _calc_tornado(reference, scale, cutbyref, data, sens_filter):
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
                    sens_filter=sens_filter,
                    plotly_theme=self.plotly_theme,
                    reference=reference,
                    scale=scale,
                    cutbyref="Cut by reference" in cutbyref,
                    number_format=data.get("number_format", ""),
                    unit=data.get("unit", ""),
                    spaced=data.get("spaced", True),
                    locked_si_prefix=data.get("locked_si_prefix", None),
                )
            except KeyError:
                return {}, {}

        if self.allow_click:

            @app.callback(
                Output(self.ids("click-store"), "data"),
                [
                    Input(self.ids("tornado-graph"), "clickData"),
                    Input(self.ids("reset"), "n_clicks"),
                ],
            )
            def _save_click_data(data, nclicks):
                if dash.callback_context.triggered is None:
                    raise PreventUpdate

                ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

                if ctx == self.ids("reset") and nclicks:

                    return json.dumps(
                        {
                            "real_low": [],
                            "real_high": [],
                            "sens_name": None,
                        }
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
                except TypeError as exc:
                    raise PreventUpdate from exc


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
# pylint: disable=too-many-arguments
def tornado_plot(
    realizations,
    data,
    sens_filter,
    plotly_theme,
    reference="rms_seed",
    scale="Percentage",
    cutbyref=True,
    number_format="",
    unit="",
    spaced=True,
    locked_si_prefix=None,
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

    df = calc_tornado_df(data, realizations, ref_avg, scale)

    # Drops sensitivities smaller than reference if specified
    if cutbyref and df["sensname"].str.contains(reference).any():
        df = cut_by_ref(df, reference)

    df = df.loc[df["sensname"].isin(sens_filter)]
    df = sort_by_max(df)

    store_low_high = {
        sensname: {
            "real_low": sens_name_df["low_reals"].tolist()[0],
            "real_high": sens_name_df["high_reals"].tolist()[0],
        }
        for sensname, sens_name_df in df.groupby(["sensname"])
    }

    # If percentage, unit is % and we turn off SI-prefix
    if scale == "Percentage":
        unit_x = "%"
        locked_si_prefix_relative = 0
    else:
        unit_x = unit
        locked_si_prefix_relative = locked_si_prefix
    # Return tornado data as Plotly figure
    plot_data = [
        dict(
            type="bar",
            y=df["sensname"],
            x=df["low"],
            name="low",
            base=df["low_base"],
            customdata=df["low_reals"],
            hovertext=[
                f"{si_prefixed(x, number_format, unit_x, spaced, locked_si_prefix_relative)}"
                f"<br>Case: {label}<br>True Value: "
                f"{si_prefixed(val, number_format, unit, spaced, locked_si_prefix)}"
                f"<br>Realizations: "
                f"{printable_int_list(reals)}"
                if reals
                else None
                for x, label, val, reals in zip(
                    df["low_tooltip"],
                    df["low_label"],
                    df["true_low"],
                    df["low_reals"],
                )
            ],
            hoverinfo="text",
            orientation="h",
        ),
        dict(
            type="bar",
            y=df["sensname"],
            x=df["high"],
            name="high",
            base=df["high_base"],
            customdata=df["high_reals"],
            hovertext=[
                f"{si_prefixed(x, number_format, unit_x, spaced, locked_si_prefix_relative)}"
                f"<br>Case: {label}<br>True Value: "
                f"{si_prefixed(val, number_format, unit, spaced, locked_si_prefix)}"
                f"<br>Realizations: "
                f"{printable_int_list(reals)}"
                if reals
                else None
                for x, label, val, reals in zip(
                    df["high_tooltip"],
                    df["high_label"],
                    df["true_high"],
                    df["high_reals"],
                )
            ],
            hoverinfo="text",
            orientation="h",
        ),
    ]
    layout = {}
    layout.update(plotly_theme["layout"])
    layout.update(
        {
            "barmode": "relative",
            "margin": {"l": 0, "r": 0, "b": 20, "t": 50},
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
                "dtick": 1,
            },
            "showlegend": False,
            "hovermode": "y",
            "annotations": [
                {
                    "x": 0,
                    "y": len(list(df["low"])),
                    "xref": "x",
                    "yref": "y",
                    "text": f"Reference avg: "
                    f"{si_prefixed(ref_avg, number_format, unit, spaced, locked_si_prefix)}",
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
    return (
        {"data": plot_data, "layout": layout},
        store_low_high,
    )


# pylint: disable=too-many-locals
def calc_tornado_df(data, realizations, ref_avg, scale):
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
                        "reals": list(map(int, sens_case_df["REAL"])),
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
            low_reals = list(map(int, case_df.loc[case_df["VALUE"] <= ref_avg]["REAL"]))

            # Extract list of realizations with values higher then reference avg (high)
            high_reals = list(map(int, case_df.loc[case_df["VALUE"] > ref_avg]["REAL"]))

            arr.append(
                {
                    "sensname": sens_name,
                    "senscase": "P90",
                    "values": p90,
                    "values_ref": scale_to_ref(p90, ref_avg, scale),
                    "reals": low_reals,
                }
            )
            arr.append(
                {
                    "sensname": sens_name,
                    "senscase": "P10",
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
        low = sens_name_df.copy().loc[sens_name_df["values_ref"].idxmin()]
        high = sens_name_df.copy().loc[sens_name_df["values_ref"].idxmax()]
        if sens_name_df["senscase"].nunique() == 1:
            # Single case sens, implies low == high, but testing just in case:
            if low["values_ref"] != high["values_ref"]:
                raise ValueError(
                    "For a single sensitivity case, low and high cases should be equal. Likely bug"
                )
            if low["values_ref"] < 0:
                # To avoid warnings for changing values of dataframe slices.
                high = high.copy()
                high["values_ref"] = 0
                high["reals"] = []
                high["senscase"] = None
                high["values"] = ref_avg
            else:
                low = (
                    low.copy()
                )  # To avoid warnings for changing values of dataframe slices.
                low["values_ref"] = 0
                low["reals"] = []
                low["senscase"] = None
                low["values"] = ref_avg

        arr2.append(
            {
                "low": calc_low_x(low["values_ref"], high["values_ref"]),
                "low_base": calc_low_base(low["values_ref"], high["values_ref"]),
                "low_label": low["senscase"],
                "low_tooltip": low["values_ref"],
                "true_low": low["values"],
                "low_reals": low["reals"],
                "sensname": sensname,
                "high": calc_high_x(low["values_ref"], high["values_ref"]),
                "high_base": calc_high_base(low["values_ref"], high["values_ref"]),
                "high_label": high["senscase"],
                "high_tooltip": high["values_ref"],
                "true_high": high["values"],
                "high_reals": high["reals"],
            }
        )
    return pd.DataFrame(arr2)


def calc_low_base(low, high):
    """
    From the low and high value of a parameter,
    calculates the base (starting x value) of the
    bar visualizing low values.
    >>> calc_low_base(1, 2)
    1
    >>> calc_low_base(-2, -1)
    -1
    >>> calc_low_base(-1, 1)
    0
    """
    if low < 0:
        return min(0, high)
    return low


def calc_high_base(low, high):
    """
    From the low and high value of a parameter,
    calculates the base (starting x value) of the bar
    visualizing high values.
    >>> calc_high_base(1, 2)
    1
    >>> calc_high_base(-1, 1)
    0
    >>> calc_high_base(1, 2)
    1
    """
    if high > 0:
        return max(0, low)
    return high


def calc_high_x(low, high):
    """
    From the low and high value of a parameter,
    calculates the x-value (length of bar) of the bar
    visualizing high values.
    >>> calc_high_x(-1, 1)
    1
    >>> calc_high_x(0.5, 1)
    0.5
    >>> calc_high_x(-4, -3)
    0
    """
    if high > 0:
        base = max(0, low)
        return high - base
    return 0


def calc_low_x(low, high):
    """
    From the low and high value of a parameter,
    calculates the x-value (length of bar) of the bar
    visualizing low values.
    >>> calc_low_x(-1, 1)
    -1
    >>> calc_low_x(-1, -0.5)
    -0.5
    >>> calc_low_x(1, 3)
    0
    """
    if low < 0:
        base = min(0, high)
        return low - base
    return 0


def printable_int_list(integer_list: Optional[List[int]]):
    """Creates a string out of a list of integers.
    The string gives a range x-y if all the integers between and
    including x and y are in the list, otherwise separated by commas.
    Example: the list [0, 1, 2, 4, 5, 8, 10] becomes '0-2, 4-5, 8, 10'
    If the input is `None` or the list is empty, the string 'None' is returned.
    """
    if not integer_list:
        return "None"

    sorted_list = sorted(integer_list)
    prev_number = sorted_list[0]
    string = str(prev_number)

    for next_number in sorted_list[1:]:
        if next_number > prev_number + 1:
            string += (
                f"{prev_number}" if string.endswith("-") else ""
            ) + f", {next_number}"
        elif not string.endswith("-"):
            string += "-"
        prev_number = next_number

    if not string.endswith(f", {prev_number}") and string != str(prev_number):
        string += str(prev_number)
    return string
