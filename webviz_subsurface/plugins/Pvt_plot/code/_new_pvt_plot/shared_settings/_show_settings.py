from typing import List
from dash.development.base_component import Component

from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

class ShowPlots(SettingsGroupABC):
    class Ids:
        SHOWPLOTS = "show-plots"

    def __init__(self) -> None:
        super().__init__("Show Plots")
        self.plot_settings = ["Formation Volume Factor", "Viscosity", "Density", "Gas/Oil Ratio (Rs)"]

    def layout(self) -> List[Component]:
        return [
                wcc.Checklist(
                id = self.register_component_unique_id(ShowPlots.Ids.SHOWPLOTS),
                options =[
                    {"label": x, "value":x} for x in self.plot_settings
                    ],
                value =self.plot_settings,
                vertical= True
                ),
        ]