from typing import Dict, List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        SHOW_PLOTS = "show-plots"

    def __init__(self) -> None:
        super().__init__("Show Plots")

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
        component_id = self.register_component_unique_id(ViewSettings.Ids.SHOW_PLOTS)
        return [
            wcc.Checklist(
                id={"id": component_id, "plot": plot_value},
                options=[{"label": plot_label, "value": plot_value}],
                value=[plot_value],
                persistence=False,
            )
            for plot_value, plot_label in self.plot_visibility_options().items()
        ]
