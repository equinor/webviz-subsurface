from typing import List

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import LineType


class Visualization(SettingsGroupABC):
    class Ids(StrEnum):
        REALIZATION_OR_MEAN = "realization-or-mean"
        BOTTOM_VISUALIZATION = "bottom-visualization"

    def __init__(
        self,
    ) -> None:
        super().__init__("Visualization")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.REALIZATION_OR_MEAN),
                options=[
                    {"label": "Individual realizations", "value": LineType.REALIZATION},
                    {"label": "Mean over Sensitivities", "value": LineType.STATISTICS},
                ],
                value=LineType.REALIZATION,
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=wcc.RadioItems(
                    label="Bottom visualization:",
                    id=self.register_component_unique_id(self.Ids.BOTTOM_VISUALIZATION),
                    options=[
                        {"label": "Table", "value": "table"},
                        {"label": "Realization plot", "value": "realplot"},
                    ],
                    vertical=False,
                    value="table",
                ),
            ),
        ]
