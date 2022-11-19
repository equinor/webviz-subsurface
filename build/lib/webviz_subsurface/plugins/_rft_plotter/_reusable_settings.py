from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class FilterLayout(SettingsGroupABC):
    class Ids(StrEnum):
        FILTER_WELLS = "filter-wells"
        FILTER_ZONES = "filter-zones"
        FILTER_DATES = "filter-dates"

    def __init__(self, wells: List[str], zones: List[str], dates: List[str]) -> None:
        super().__init__("Filters")
        self._wells = wells
        self._zones = zones
        self._dates = dates

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Wells",
                size=min(10, len(self._wells)),
                id=self.register_component_unique_id(self.Ids.FILTER_WELLS),
                options=[{"label": name, "value": name} for name in self._wells],
                value=self._wells,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Zones",
                size=min(10, len(self._zones)),
                id=self.register_component_unique_id(self.Ids.FILTER_ZONES),
                options=[{"label": name, "value": name} for name in self._zones],
                value=self._zones,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Dates",
                size=min(10, len(self._dates)),
                id=self.register_component_unique_id(self.Ids.FILTER_DATES),
                options=[{"label": name, "value": name} for name in self._dates],
                value=self._dates,
                multi=True,
            ),
        ]
