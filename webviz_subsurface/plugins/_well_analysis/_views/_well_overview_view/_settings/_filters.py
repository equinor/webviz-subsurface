from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class WellOverviewFilters(SettingsGroupABC):
    class Ids(StrEnum):
        SELECTED_WELLS = "selected-wells"

    def __init__(self, wells: List[str]) -> None:
        super().__init__("Filters")
        self._wells = wells

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(self._wells)),
                id=self.register_component_unique_id(
                    WellOverviewFilters.Ids.SELECTED_WELLS
                ),
                options=[{"label": well, "value": well} for well in self._wells],
                value=self._wells,
                multi=True,
            )
        ]
