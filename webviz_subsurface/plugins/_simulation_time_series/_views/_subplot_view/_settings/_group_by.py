from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._types import SubplotGroupByOptions


class GroupBySettings(SettingsGroupABC):
    class Ids(StrEnum):
        SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS = "subplot-owner-options-radio-items"

    def __init__(self) -> None:
        super().__init__("Group by")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    GroupBySettings.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ),
                options=[
                    {
                        "label": "Time Series",
                        "value": SubplotGroupByOptions.VECTOR,
                    },
                    {
                        "label": "Ensemble",
                        "value": SubplotGroupByOptions.ENSEMBLE,
                    },
                ],
                value=SubplotGroupByOptions.VECTOR,
            )
        ]
