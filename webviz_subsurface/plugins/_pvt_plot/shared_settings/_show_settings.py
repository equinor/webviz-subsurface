from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

import webviz_core_components as wcc
from typing import Dict, List, Tuple

from .._plugin_ids import PluginIds


class ShowPlots(SettingsGroupABC):

    # pylint: disable=too-few-public-methods
    class Ids:
        SHOWPLOTS = "show-plots"

    def __init__(self) -> None:
        super().__init__("Show Plots")

        self.plot_settings = [
            "Formation Volume Factor",
            "Viscosity",
            "Density",
            "Gas/Oil Ratio (Rs)",
        ]

    @staticmethod
    def plot_visibility_options(phase: str = "") -> Dict[str, str]:
        options = {
            "fvf": "Formation Volume Factor",
            "viscosity": "Viscosity",
            "density": "Density",
            "ratio": "Gas/Oil Ratio (Rs)",
        }
        if phase == "OIL":
            options["ratio"] = "Gas/Oil Ratio (Rs)"
        if phase == "GAS":
            options["ratio"] = "Vaporized Oil Ratio (Rv)"
        if phase == "WATER":
            options.pop("ratio")
        return options

    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                id=self.register_component_unique_id(ShowPlots.Ids.SHOWPLOTS),
                options=[
                    {"label": l, "value": v}
                    for v, l in self.plot_visibility_options().items()
                ],
                value=list(self.plot_visibility_options().keys()),
                vertical=True,
                persistence=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_SHOW_PLOTS), "data"
            ),
            Input(
                self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(), "value"
            ),
        )
        def _update_show_plots(selected_plots: List[str]) -> List[str]:
            return selected_plots

        @callback(
            [
                Output(
                    self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(),
                    "options",
                ),
                Output(
                    self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(),
                    "value",
                ),
            ],
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_SHOW_PLOTS), "data"
            ),
        )
        def _set_available_plots(
            phase: str,
            values: List[str],
        ) -> Tuple[List[dict], List[str]]:
            visibility_options = self.plot_visibility_options(phase)
            return (
                [{"label": l, "value": v} for v, l in visibility_options.items()],
                [value for value in values if value in visibility_options],
            )
