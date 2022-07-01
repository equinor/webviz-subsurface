from typing import List, Tuple, Dict
from dash.development.base_component import Component
from dash import callback, Input, Output, State

import pandas as pd
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PluginIds
from ._filter import Filter

class ShowPlots(SettingsGroupABC):
    class Ids:
        SHOWPLOTS = "show-plots"

    def __init__(self, pvt_df: pd.DataFrame) -> None:
        super().__init__("Show Plots")

        self.plot_settings = ["Formation Volume Factor", "Viscosity", "Density", "Gas/Oil Ratio (Rs)"]


    @staticmethod
    def plot_visibility_options(phase: str = "") -> Dict[str, str]:
        options = {
            "fvf": "Formation Volume Factor",
            "viscosity": "Viscosity",
            "density": "Density",
        }
        if phase == "Oil (PVTO)":
            options["ratio"] = "Gas/Oil Ratio (Rs)"
        if phase == "Gas (PVTG)":
            options["ratio"] = "Vaporized Oil Ratio (Rv)"
        #print(options)
        return options


    def layout(self) -> List[Component]:
        print(self.plot_visibility_options())
        return [
                wcc.Checklist(
                id = self.register_component_unique_id(ShowPlots.Ids.SHOWPLOTS),
                options = [
                    {"label": l, "value":v} for v,l in self.plot_visibility_options().items()
                    ],
                value = [v for v in self.plot_visibility_options().values()],
                vertical= True
                ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_SHOW_PLOTS),'data'),
            Input(self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(),'value')
        )
        def _update_show_plots(selected_plots: List[str]) -> List[str]:
            return selected_plots

        @callback(
            [
                Output(self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(), "options"),
                Output(self.component_unique_id(ShowPlots.Ids.SHOWPLOTS).to_string(), "value"),
            ],
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_SHOW_PLOTS), "data"),
        )
        def _set_available_plots(
            phase: str,
            values: List[str],
        ) -> Tuple[List[dict], List[str]]:
            print ("Selected phase is ", phase)
            visibility_options = self.plot_visibility_options(phase)
            print ("New option is ", visibility_options)
            return (
                [{"label": l, "value": v} for v, l in visibility_options.items()],
                [value for value in values if value in visibility_options],
            )