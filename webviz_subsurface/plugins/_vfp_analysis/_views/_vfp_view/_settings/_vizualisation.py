from typing import Any, List

import webviz_core_components as wcc
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Vizualisation(SettingsGroupABC):
    class Ids(StrEnum):
        COLOR_BY = "color-by"

    def __init__(self, vfp_names: List[str]) -> None:
        super().__init__("Vizualisation")
        self._vfp_names = vfp_names

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Vizualisation.Ids.COLOR_BY),
                label="Color by",
                options=[
                    {"label": "THP", "value": "thp"},
                    {"label": "WFR", "value": "wfr"},
                    {"label": "GFR", "value": "gfr"},
                    {"label": "ALQ", "value": "alq"},
                ],
                clearable=False,
                value="thp",
                persistence=True,
                persistence_type="session",
            )
        ]
