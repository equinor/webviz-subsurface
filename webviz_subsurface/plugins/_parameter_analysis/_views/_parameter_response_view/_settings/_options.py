from typing import List

import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ParamRespOptions(SettingsGroupABC):
    class Ids(StrEnum):
        VECTOR_FILTER = "vector-filter"
        SUBMIT_VECTOR_FILTER = "submit-vector-filter"
        VECTOR_FILTER_STORE = "vector-filter-store"
        AUTO_COMPUTE_CORRELATIONS = "auto-compute-correlations"

    def __init__(
        self,
    ) -> None:
        super().__init__("Correlation Options")

    def layout(self) -> List[Component]:
        return [
            html.Header("Vectors for parameter correlation"),
            dcc.Textarea(
                id=self.register_component_unique_id(self.Ids.VECTOR_FILTER),
                style={"width": "95%", "height": "60px", "resize": "none"},
                placeholder="\nenter comma separated input\n* is used as wildcard",
                persistence=True,
                persistence_type="session",
            ),
            html.Button(
                "Submit",
                id=self.register_component_unique_id(self.Ids.SUBMIT_VECTOR_FILTER),
                style={
                    "marginBottom": "5px",
                    "width": "100%",
                    "height": "20px",
                    "line-height": "20px",
                    "background-color": "#E8E8E8",
                },
            ),
            dcc.Store(
                id=self.register_component_unique_id(self.Ids.VECTOR_FILTER_STORE)
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(
                    self.Ids.AUTO_COMPUTE_CORRELATIONS
                ),
                options=[
                    {"label": "Calculate correlations", "value": "AutoCompute"},
                ],
                value=["AutoCompute"],
            ),
        ]
