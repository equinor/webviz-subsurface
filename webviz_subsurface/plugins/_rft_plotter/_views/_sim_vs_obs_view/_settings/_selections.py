from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class PlotType(StrEnum):
    CROSSPLOT = "crossplot"
    ERROR_BOXPLOT = "error-boxplot"


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        PLOT_TYPE = "plot-type"
        ENSEMBLES = "ensembles"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Selections")
        self._ensembles = ensembles

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label="Plot Type",
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
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(self.Ids.ENSEMBLES),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=[self._ensembles[0] if len(self._ensembles) > 0 else None],
                clearable=False,
                multi=True,
            ),
        ]
