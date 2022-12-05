from typing import Any, List

import webviz_core_components as wcc
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import PressureType


class PressureOption(SettingsGroupABC):
    class Ids(StrEnum):
        PRESSURE_OPTION = "pressure-option"

    def __init__(self) -> None:
        super().__init__("Pressure Option")

    def layout(self) -> List[Any]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    PressureOption.Ids.PRESSURE_OPTION
                ),
                options=[
                    {"label": "BHP", "value": PressureType.BHP},
                    {"label": "DP (BHP-THP)", "value": PressureType.DP},
                ],
                value=PressureType.BHP,
                persistence=True,
                persistence_type="session",
            )
        ]
