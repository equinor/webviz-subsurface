from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import VisualizationType


class ParamDistVisualizationType(SettingsGroupABC):
    class Ids(StrEnum):
        VISUALIZATION_TYPE = "visualization-type"

    def __init__(self) -> None:
        super().__init__("Visualization Type")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.VISUALIZATION_TYPE),
                options=[
                    {"label": "Histogram", "value": VisualizationType.HISTOGRAM},
                    {
                        "label": "Distribution plots",
                        "value": VisualizationType.DISTRIBUTION,
                    },
                    {"label": "Box plots", "value": VisualizationType.BOX},
                    {
                        "label": "Statistics table",
                        "value": VisualizationType.STAT_TABLE,
                    },
                ],
                value=VisualizationType.HISTOGRAM,
                vertical=True,
            )
        ]
