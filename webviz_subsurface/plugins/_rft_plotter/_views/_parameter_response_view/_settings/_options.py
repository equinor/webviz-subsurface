from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Options(SettingsGroupABC):
    class Ids(StrEnum):
        CORRTYPE = "param-response-corrtype"
        DEPTHOPTION = "paramresp-depthoption"

    def __init__(self) -> None:
        super().__init__("Options")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label="Correlation options",
                id=self.register_component_unique_id(self.Ids.CORRTYPE),
                options=[
                    {
                        "label": "Simulated vs parameters",
                        "value": "sim_vs_param",
                    },
                    {
                        "label": "Parameter vs simulated",
                        "value": "param_vs_sim",
                    },
                ],
                value="sim_vs_param",
            ),
            wcc.RadioItems(
                label="Depth option",
                id=self.register_component_unique_id(self.Ids.DEPTHOPTION),
                options=[
                    {
                        "label": "TVD",
                        "value": "TVD",
                    },
                    {
                        "label": "MD",
                        "value": "MD",
                    },
                ],
                value="TVD",
            ),
        ]
