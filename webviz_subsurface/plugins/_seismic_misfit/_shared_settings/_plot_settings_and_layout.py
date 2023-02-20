from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class PlotSettingsAndLayout(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        LAYOUT_HEIGHT = "layout-height"
        LAYOUT_COLUMNS = "layout-columns"
        X_AXIS_SETTINGS = "x-axix-settings"
        SUPERIMPOSE_PLOT = "superimpose-plot"

    def __init__(self) -> None:
        super().__init__("Plot settings and layout")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Fig layout - height",
                id=self.register_component_unique_id(self.Ids.LAYOUT_HEIGHT),
                options=[
                    {
                        "label": "Very small",
                        "value": 250,
                    },
                    {
                        "label": "Small",
                        "value": 350,
                    },
                    {
                        "label": "Medium",
                        "value": 450,
                    },
                    {
                        "label": "Large",
                        "value": 700,
                    },
                    {
                        "label": "Very large",
                        "value": 1000,
                    },
                ],
                value=450,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Fig layout - # columns",
                id=self.register_component_unique_id(self.Ids.LAYOUT_COLUMNS),
                options=[
                    {
                        "label": "One column",
                        "value": 1,
                    },
                    {
                        "label": "Two columns",
                        "value": 2,
                    },
                    {
                        "label": "Three columns",
                        "value": 3,
                    },
                ],
                style={"display": "block"},
                value=1,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]
