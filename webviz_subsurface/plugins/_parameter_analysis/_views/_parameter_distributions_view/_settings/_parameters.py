from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ParamDistParameters(SettingsGroupABC):
    class Ids(StrEnum):
        SORT_BY = "sort-by"
        PARAMETERS = "parameters"

    def __init__(self, parameters: List[str]) -> None:
        super().__init__("Parameters")
        if not parameters:
            raise ValueError("List of parameters can't be empty.")
        self._parameters = parameters

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label="Sort parameters by",
                id=self.register_component_unique_id(self.Ids.SORT_BY),
                className="block-options",
                options=[
                    {"label": "Name", "value": "Name"},
                    {
                        "label": "Standard deviation",
                        "value": "Stddev",
                    },
                    {
                        "label": "Average",
                        "value": "Avg",
                    },
                ],
                value="Name",
            ),
            wcc.SelectWithLabel(
                label="Select parameters",
                id=self.register_component_unique_id(self.Ids.PARAMETERS),
                options=[{"label": i, "value": i} for i in self._parameters],
                value=[self._parameters[0]],
                multi=True,
                size=min(40, len(self._parameters)),
            ),
        ]
