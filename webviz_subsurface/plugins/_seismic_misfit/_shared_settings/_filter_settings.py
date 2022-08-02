from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class FilterSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        REGION_SELECTOR = "region-selector"
        REALIZATION_SELECTOR = "realization-selector"

    def __init__(self, region_names: List[int], realizations: List) -> None:
        super().__init__("Filter sttings")
        self.region_names = region_names
        self.realizations = realizations

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Region selector",
                id=self.register_component_unique_id(self.Ids.REGION_SELECTOR),
                options=[
                    {"label": regno, "value": regno} for regno in self.region_names
                ],
                value=self.region_names,
                size=min([len(self.region_names), 5]),
            ),
            wcc.SelectWithLabel(
                label="Realization selector",
                id=self.register_component_unique_id(self.Ids.REALIZATION_SELECTOR),
                options=[{"label": real, "value": real} for real in self.realizations],
                value=self.realizations,
                size=min([len(self.realizations), 5]),
            ),
        ]
