from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import ColorAndSizeByType


class SizeColorSettings(SettingsGroupABC):
    class Ids(StrEnum):
        CROSSPLOT_COLOR_BY = "crossplot-color-by"
        CROSSPLOT_SIZE_BY = "crossplot-size-by"

    def __init__(self) -> None:
        super().__init__("Crossplot options")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(self.Ids.CROSSPLOT_COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": ColorAndSizeByType.MISFIT,
                    },
                    {
                        "label": "Standard Deviation",
                        "value": ColorAndSizeByType.STDDEV,
                    },
                ],
                value=ColorAndSizeByType.STDDEV,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size by",
                id=self.register_component_unique_id(self.Ids.CROSSPLOT_SIZE_BY),
                options=[
                    {
                        "label": "Standard Deviation",
                        "value": ColorAndSizeByType.STDDEV,
                    },
                    {
                        "label": "Misfit",
                        "value": ColorAndSizeByType.MISFIT,
                    },
                ],
                value=ColorAndSizeByType.MISFIT,
                clearable=False,
            ),
        ]
