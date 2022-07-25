from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._business_logic import RftPlotterDataModel


class SizeColorLayout(SettingsGroupABC):
    class Ids:
        CROSSPLOT_COLOR_BY = "crossplot-color-by"
        CROSSPLOT_SIZE_BY = "crossplot-size-by"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Plot settings")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(self.Ids.CROSSPLOT_COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                ],
                value="STDDEV",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size by",
                id=self.register_component_unique_id(self.Ids.CROSSPLOT_SIZE_BY),
                options=[
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                ],
                value="ABSDIFF",
                clearable=False,
            ),
        ]
