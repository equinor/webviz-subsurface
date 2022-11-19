import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import pandas as pd
import webviz_core_components as wcc
from dash import (
    ClientsideFunction,
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dash_table,
    dcc,
    html,
)
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface

from ._tornado_bar_chart import TornadoBarChart
from ._tornado_data import TornadoData
from ._tornado_table import TornadoTable


class TornadoWidget:
    """### TornadoWidget

    This component visualizes a Tornado plot.
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
        app: Dash,
        webviz_settings: WebvizSettings,
        realizations: pd.DataFrame,
        reference: str = "rms_seed",
        allow_click: bool = False,
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
        self.plotly_theme = webviz_settings.theme.plotly_theme
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "clientside_functions.js"
        )
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self) -> List[Dict[str, Any]]:
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
    def storage_id(self) -> str:
        """The id of the dcc.Store component that holds the tornado data"""
        return self.ids("storage")

    @property
    def click_id(self) -> str:
        """The id of the dcc.Store component that holds click data"""
        return self.ids("click-store")

    @property
    def high_low_storage_id(self) -> str:
        """The id of the dcc.Store component that holds click data"""
        return self.ids("high-low-storage")

    @property
    def settings_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    children=[
                        wcc.FlexBox(
                            style={"fontSize": "15px"},
                            children=[
                                html.Div(
                                    style={
                                        "minWidth": "100px",
                                        "flex": 2,
                                        "marginRight": "10px",
                                    },
                                    children=[
                                        wcc.Dropdown(
                                            label="Reference",
                                            id=self.ids("reference"),
                                            options=[
                                                {
                                                    "label": r,
                                                    "value": r,
                                                }
                                                for r in self.sensnames
                                            ],
                                            value=self.initial_reference,
                                            clearable=False,
                                        ),
                                        wcc.Dropdown(
                                            label="Scale",
                                            id=self.ids("scale"),
                                            options=[
                                                {
                                                    "label": r,
                                                    "value": r,
                                                }
                                                for r in [
                                                    "Relative value (%)",
                                                    "Relative value",
                                                    "True value",
                                                ]
                                            ],
                                            value="Relative value (%)",
                                            clearable=False,
                                        ),
                                        html.Button(
                                            style={
                                                "fontSize": "10px",
                                                "marginTop": "10px",
                                            }
                                            if self.allow_click
                                            else {"display": "none"},
                                            id=self.ids("reset"),
                                            children="Clear selected",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={
                                        "minWidth": "100px",
                                        "flex": 2,
                                        "marginRight": "10px",
                                    },
                                    children=[
                                        wcc.SelectWithLabel(
                                            label="Select sensitivities",
                                            id=self.ids("sens_filter"),
                                            options=[
                                                {
                                                    "label": i,
                                                    "value": i,
                                                }
                                                for i in self.sensnames
                                            ],
                                            value=self.sensnames,
                                            multi=True,
                                            size=min(
                                                8,
                                                len(self.sensnames),
                                            ),
                                        ),
                                    ],
                                ),
                                html.Div(
                                    style={
                                        "minWidth": "100px",
                                        "flex": 3,
                                    },
                                    children=[
                                        wcc.Checklist(
                                            label="Plot options",
                                            id=self.ids("plot-options"),
                                            options=[
                                                {
                                                    "label": "Fit all bars in figure",
                                                    "value": "Fit all bars in figure",
                                                },
                                                {
                                                    "label": "Remove sensitivites with no impact",
                                                    "value": "Remove sensitivites with no impact",
                                                },
                                                {
                                                    "label": "Show realization points",
                                                    "value": "Show realization points",
                                                },
                                                {
                                                    "label": "Color bars by sensitivity",
                                                    "value": "Color bars by sensitivity",
                                                },
                                            ],
                                            value=[],
                                            labelStyle={"display": "block"},
                                        ),
                                        wcc.Dropdown(
                                            label="Label",
                                            id=self.ids("label"),
                                            options=[
                                                {"label": "No label", "value": "hide"},
                                                {
                                                    "label": "Simple label",
                                                    "value": "simple",
                                                },
                                                {
                                                    "label": "Detailed label",
                                                    "value": "detailed",
                                                },
                                            ],
                                            value="detailed",
                                            clearable=False,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            style={"marginLeft": "10px", "height": "90vh"},
            children=[
                html.Div(
                    children=[
                        html.Label(
                            "Tornado Plot",
                            style={
                                "textAlign": "center",
                                "font-weight": "bold",
                            },
                        ),
                        wcc.RadioItems(
                            vertical=False,
                            id=self.ids("plot-or-table"),
                            options=[
                                {"label": "Show bars", "value": "bars"},
                                {
                                    "label": "Show table",
                                    "value": "table",
                                },
                            ],
                            value="bars",
                        ),
                    ],
                ),
                html.Div(
                    style={"overflowY": "auto", "height": "60vh"},
                    children=[
                        html.Div(
                            id=self.ids("graph-wrapper"),
                            style={},
                            children=wcc.Graph(
                                id=self.ids("tornado-graph"),
                                config={"displayModeBar": False},
                            ),
                        ),
                        html.Div(
                            id=self.ids("table-wrapper"),
                            style={"display": "none"},
                            children=dash_table.DataTable(
                                id=self.ids("tornado-table"),
                                style_cell={
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                },
                            ),
                        ),
                    ],
                ),
                html.Hr(style={"marginTop": "10px"}),
                self.settings_layout,
                dcc.Store(id=self.ids("storage"), storage_type="session"),
                dcc.Store(id=self.ids("click-store"), storage_type="session"),
                dcc.Store(id=self.ids("high-low-storage"), storage_type="session"),
                dcc.Store(id=self.ids("client-height-pixels"), storage_type="session"),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.ids("label"), "disabled"),
            Input(self.ids("plot-options"), "value"),
        )
        def _disable_label(plot_options: List) -> bool:
            return "Show realization points" in plot_options

        @app.callback(
            Output(self.ids("graph-wrapper"), "style"),
            Output(self.ids("table-wrapper"), "style"),
            Input(self.ids("plot-or-table"), "value"),
            State(self.ids("graph-wrapper"), "style"),
            State(self.ids("table-wrapper"), "style"),
        )
        def _set_visualization(
            viz_type: str, graph_style: dict, table_style: dict
        ) -> Tuple[Dict[str, str], Dict[str, str]]:
            if viz_type == "bars":
                graph_style.update({"display": "inline"})
                table_style.update({"display": "none"})
            if viz_type == "table":
                graph_style.update({"display": "none"})
                table_style.update({"display": "inline"})
            return graph_style, table_style

        app.clientside_callback(
            ClientsideFunction(
                namespace="clientside", function_name="get_client_height"
            ),
            Output(self.ids("client-height-pixels"), "data"),
            Input(self.ids("plot-options"), "value"),
        )

        @app.callback(
            Output(self.ids("tornado-graph"), "figure"),
            Output(self.ids("tornado-table"), "data"),
            Output(self.ids("tornado-table"), "columns"),
            Output(self.ids("high-low-storage"), "data"),
            Input(self.ids("reference"), "value"),
            Input(self.ids("scale"), "value"),
            Input(self.ids("plot-options"), "value"),
            Input(self.ids("label"), "value"),
            Input(self.ids("storage"), "data"),
            Input(self.ids("sens_filter"), "value"),
            State(self.ids("client-height-pixels"), "data"),
        )
        def _calc_tornado(
            reference: str,
            scale: str,
            plot_options: List,
            label_option: str,
            data: Union[str, bytes, bytearray],
            sens_filter: List[str],
            client_height: Optional[int],
        ) -> Tuple[Any, List[Any], List[Dict[Any, Any]], Dict[str, Dict[Any, Any]]]:
            if not data:
                raise PreventUpdate
            plot_options = plot_options if plot_options else []
            data = json.loads(data)
            if not isinstance(data, dict):
                raise PreventUpdate
            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self.realizations.loc[
                self.realizations["ENSEMBLE"] == data["ENSEMBLE"]
            ]

            design_and_responses = pd.merge(values, realizations, on="REAL")
            if sens_filter is not None:
                if reference not in sens_filter:
                    sens_filter.append(reference)
                design_and_responses = design_and_responses.loc[
                    design_and_responses["SENSNAME"].isin(sens_filter)
                ]
            tornado_data = TornadoData(
                dframe=design_and_responses,
                response_name=data.get("response_name"),
                reference=reference,
                scale="Percentage" if scale == "Relative value (%)" else "Absolute",
                cutbyref="Remove sensitivites with no impact" in plot_options,
            )

            figure_height = (
                client_height * 0.59
                if "Fit all bars in figure" in plot_options
                and client_height is not None
                else max(100 * len(tornado_data.tornadotable["sensname"].unique()), 200)
            )
            tornado_figure = TornadoBarChart(
                tornado_data=tornado_data,
                plotly_theme=self.plotly_theme,
                figure_height=figure_height,
                label_options=label_option,
                number_format=data.get("number_format", ""),
                unit=data.get("unit", ""),
                spaced=data.get("spaced", True),
                locked_si_prefix=data.get("locked_si_prefix", None),
                use_true_base=scale == "True value",
                show_realization_points="Show realization points" in plot_options,
                color_by_sensitivity="Color bars by sensitivity" in plot_options,
            )
            tornado_table = TornadoTable(tornado_data=tornado_data)
            return (
                tornado_figure.figure,
                tornado_table.as_plotly_table,
                tornado_table.columns,
                tornado_data.low_high_realizations_list,
            )

        if self.allow_click:

            @app.callback(
                Output(self.ids("click-store"), "data"),
                [
                    Input(self.ids("tornado-graph"), "clickData"),
                    Input(self.ids("reset"), "n_clicks"),
                    State(self.ids("high-low-storage"), "data"),
                ],
            )
            def _save_click_data(
                data: dict, nclicks: Optional[int], sens_reals: dict
            ) -> str:
                if (
                    callback_context.triggered is None
                    or sens_reals is None
                    or data is None
                ):
                    raise PreventUpdate
                ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
                if ctx == self.ids("reset") and nclicks:
                    return json.dumps(
                        {
                            "real_low": [],
                            "real_high": [],
                            "sens_name": None,
                        }
                    )
                sensname = data["points"][0]["y"]
                real_high = sens_reals[sensname]["real_high"]
                real_low = sens_reals[sensname]["real_low"]
                return json.dumps(
                    {
                        "real_low": real_low,
                        "real_high": real_high,
                        "sens_name": sensname,
                    }
                )
