import webviz_core_components as wcc
from dash import dcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class InfoBox(ViewElementABC):
    def __init__(self, label: str, caseinfo: str) -> None:
        super().__init__()
        self.label = label
        self.caseinfo = caseinfo

    def inner_layout(self) -> Component:
        return wcc.Selectors(
            label=self.label,
            children=[
                dcc.Textarea(
                    value=self.caseinfo,
                    style={
                        "width": 500,
                    },
                ),
            ],
        )
