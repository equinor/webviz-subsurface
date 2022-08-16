from typing import Dict, List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ViewSettings(SettingsGroupABC):

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
        component_id = self.register_component_unique_id(ViewSettings.Ids.SHOWPLOTS)
        return [
            wcc.Checklist(
                id={"id": component_id, "plot": plot_value},
                options=[{"label": plot_label, "value": plot_value}],
                value=[plot_value],
                persistence=False,
            )
            for plot_value, plot_label in self.plot_visibility_options().items()
        ]
