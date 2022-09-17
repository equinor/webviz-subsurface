from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class Settings(SettingsGroupABC):
    class Ids(StrEnum):
        ZSCALE = "z-scale"
        SHOW_CUBEAXES = "show-cube-axes"
        SHOWGRIDLINES = "show-grid-lines"

    def __init__(self) -> None:
        super().__init__("Settings")

    def layout(self) -> List[Component]:

        return [
            wcc.Slider(
                label="Z Scale",
                id=self.register_component_unique_id(Settings.Ids.ZSCALE),
                marks={x: x for x in [1, 5, 10, 20, 50]},
                value=5,
                step=1,
                included=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(Settings.Ids.SHOW_CUBEAXES),
                options=["Show bounding box"],
                value=["Show bounding box"],
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(Settings.Ids.SHOWGRIDLINES),
                options=["Show grid lines"],
                value=["Show grid lines"],
            ),
        ]
