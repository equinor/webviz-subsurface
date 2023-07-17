from typing import List

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class SensitivityFilter(SettingsGroupABC):
    class Ids(StrEnum):
        SENSITIVITY_FILTER = "sensitivity-filter"
        SENSITIVITY_FILTER_LINK = "sensitivity-filter-link"

    def __init__(self, sensitivities: List[str]) -> None:
        super().__init__("Sensitivity Filter")
        self._sensitivities = sensitivities

    def layout(self) -> List[Component]:
        return [
            html.Div(
                style={"margin-bottom": "10px"},
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            self.Ids.SENSITIVITY_FILTER_LINK
                        ),
                        options=[
                            {
                                "label": "Apply filter only on timeseries",
                                "value": "no link",
                            }
                        ],
                        value=[],
                    ),
                ],
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(self.Ids.SENSITIVITY_FILTER),
                options=[{"label": i, "value": i} for i in self._sensitivities],
                value=self._sensitivities,
                size=min(20, len(self._sensitivities)),
            ),
        ]
