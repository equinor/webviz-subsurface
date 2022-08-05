from typing import Dict, List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


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
