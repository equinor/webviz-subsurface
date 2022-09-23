from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import CorrType, DepthType


class Options(SettingsGroupABC):
    class Ids(StrEnum):
        CORRTYPE = "corrtype"
        DEPTHTYPE = "depthtype"

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
                        "value": CorrType.SIM_VS_PARAM,
                    },
                    {
                        "label": "Parameter vs simulated",
                        "value": CorrType.PARAM_VS_SIM,
                    },
                ],
                value="sim_vs_param",
            ),
            wcc.RadioItems(
                label="Depth option",
                id=self.register_component_unique_id(self.Ids.DEPTHTYPE),
                options=[
                    {
                        "label": "TVD",
                        "value": DepthType.TVD,
                    },
                    {
                        "label": "MD",
                        "value": DepthType.MD,
                    },
                ],
                value=DepthType.TVD,
            ),
        ]
