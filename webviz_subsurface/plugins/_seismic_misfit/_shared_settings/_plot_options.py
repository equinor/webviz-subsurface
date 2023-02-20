from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class PlotOptions(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        COLOR_BY = "color-by"
        SIZE_BY = "size-by"
        SIM_ERROR_BAR = "sim-error-bar"

    def __init__(self) -> None:
        super().__init__("Plot options")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(self.Ids.COLOR_BY),
                options=[
                    {
                        "label": "none",
                        "value": None,
                    },
                    {
                        "label": "region",
                        "value": "region",
                    },
                ],
                value="region",
                clearable=True,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Size by",
                id=self.register_component_unique_id(self.Ids.SIZE_BY),
                options=[
                    {
                        "label": "none",
                        "value": None,
                    },
                    {
                        "label": "sim_std",
                        "value": "sim_std",
                    },
                    {
                        "label": "diff_mean",
                        "value": "diff_mean",
                    },
                    {
                        "label": "diff_std",
                        "value": "diff_std",
                    },
                ],
                value=None,
            ),
            wcc.Dropdown(
                label="Sim errorbar",
                id=self.register_component_unique_id(self.Ids.SIM_ERROR_BAR),
                options=[
                    {
                        "label": "None",
                        "value": None,
                    },
                    {
                        "label": "Sim std",
                        "value": "sim_std",
                    },
                    {
                        "label": "Sim p10/p90",
                        "value": "sim_p10_p90",
                    },
                ],
                value="None",
            ),
        ]
