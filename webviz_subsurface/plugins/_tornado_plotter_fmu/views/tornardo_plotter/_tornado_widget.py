import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from dash import (
    ALL,
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    callback_context,
    clientside_callback,
    dash_table,
    html,
)
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewABC

import webviz_subsurface
from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable

from ..._plugin_ids import PlugInIDs
from ...view_elements._tornardo_view_element import Label, TornadoViewElement


class TornadoWidget(ViewABC):
    """### TornadoWidget

    Edited version of the TornadoWidget in webviz subsurface components.
    Edits have been made to suuprot the WLF framework and it is spescified for the
    Tornado plotter FMU plugin

    """

    class IDs:
        # pylint: disable=too-few-public-methods
        LABEL = "label"
        TORNADO_WIDGET = "tornado-widget"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        realizations: pd.DataFrame,
        allow_click: bool = False,
    ) -> None:
        super().__init__("Tornado Widget")

        self.realizations = realizations
        self.sensnames = list(self.realizations["SENSNAME"].unique())
        if self.sensnames == [None]:
            raise KeyError(
                "No sensitivity information found in ensemble. "
                "Containers utilizing tornadoplot can only be used for ensembles with "
                "one by one design matrix setup "
                "(SENSNAME and SENSCASE must be present in parameter file)."
            )
        self.allow_click = allow_click
        self.plotly_theme = webviz_settings.theme.plotly_theme
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "clientside_functions.js"
        )

        viewcolumn = self.add_column()

        first_row = viewcolumn.make_row()
        first_row.add_view_element(Label(), TornadoWidget.IDs.LABEL)
        second_row = viewcolumn.make_row()
        second_row.add_view_element(
            TornadoViewElement(), TornadoWidget.IDs.TORNADO_WIDGET
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.BARS)
                .to_string(),
                "style",
            ),
            Output(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.TABLE_WRAPPER)
                .to_string(),
                "style",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.PlotPicker.BARS_OR_TABLE),
                "data",
            ),
            State(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.BARS)
                .to_string(),
                "style",
            ),
            State(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.TABLE_WRAPPER)
                .to_string(),
                "style",
            ),
        )
        def _set_visualization(
            viz_type: str, graph_style: dict, table_style: dict
        ) -> Tuple[Dict[str, str], Dict[str, str]]:
            if viz_type == "bars":
                graph_style.update({"display": "inline"})
                table_style.update({"display": "none"})
                return (graph_style, table_style)
            if viz_type == "table":
                graph_style.update({"display": "none"})
                table_style.update({"display": "inline"})
                return (graph_style, table_style)

        clientside_callback(
            ClientsideFunction(
                namespace="clientside", function_name="get_client_height"
            ),
            Output(
                self.get_store_unique_id(
                    PlugInIDs.Stores.DataStores.CLIENT_HIGH_PIXELS
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.PLOT_OPTIONS),
                "value",
            ),
        )

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.LABEL),
                "disabled",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.PLOT_OPTIONS),
                "value",
            ),
        )
        def _disable_label(plot_options: List) -> bool:
            if plot_options is None:
                return False
            return "Show realization points" in plot_options

        @callback(
            Output(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.BARS)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.TABLE)
                .to_string(),
                "data",
            ),
            Output(
                self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                .component_unique_id(TornadoViewElement.IDs.TABLE)
                .to_string(),
                "columns",
            ),
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.DataStores.HIGH_LOW), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.REFERENCE),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.SCALE), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.PLOT_OPTIONS),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.LABEL), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.DataStores.TORNADO_DATA),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.SENSITIVITIES),
                "data",
            ),
            State(
                self.get_store_unique_id(
                    PlugInIDs.Stores.DataStores.CLIENT_HIGH_PIXELS
                ),
                "data",
            ),
        )
        def _calc_tornado(
            reference: str,
            scale: str,
            plot_options: List,
            label_option: str,
            data: Union[str, bytes, bytearray],
            sens_filter: List[str],
            client_height: Optional[int],
        ) -> Tuple[dict, dict]:
            if not data:
                print("not data")
                raise PreventUpdate
            plot_options = plot_options if plot_options else []
            data = json.loads(data)
            print("calc torn data: ", data)
            if not isinstance(sens_filter, List):
                sens_filter = [sens_filter]
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

            @callback(
                Output(
                    self.get_store_unique_id(PlugInIDs.Stores.DataStores.CLICK_DATA),
                    "data",
                ),
                Input(
                    self.view_element(TornadoWidget.IDs.TORNADO_WIDGET)
                    .component_unique_id(TornadoWidget.IDs.BARS)
                    .to_string(),
                    "clickData",
                ),
                Input(
                    self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.RESET),
                    "n_clicks",
                ),
                State(
                    self.get_store_unique_id(PlugInIDs.Stores.DataStores.HIGH_LOW),
                    "data",
                ),
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
                if (
                    ctx
                    == self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.RESET)
                    and nclicks
                ):
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
