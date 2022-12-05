from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class PlotType(StrEnum):
    CROSSPLOT = "crossplot"
    ERROR_BOXPLOT = "error-boxplot"


class PlotTypeSettings(SettingsGroupABC):
    class Ids(StrEnum):
        PLOT_TYPE = "plot-type"

    def __init__(self) -> None:
        super().__init__("Plot Type")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.PLOT_TYPE),
                options=[
                    {
                        "label": "CrossPlot",
                        "value": PlotType.CROSSPLOT,
                    },
                    {
                        "label": "Error BoxPlot",
                        "value": PlotType.ERROR_BOXPLOT,
                    },
                ],
                value=PlotType.CROSSPLOT,
            ),
        ]
