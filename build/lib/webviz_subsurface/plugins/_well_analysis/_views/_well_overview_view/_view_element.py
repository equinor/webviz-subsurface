import webviz_core_components as wcc
from dash import html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class WellOverviewViewElement(ViewElementABC):
    class Ids(StrEnum):
        GRAPH = "graph"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div(
            children=wcc.Graph(
                id=self.register_component_unique_id(WellOverviewViewElement.Ids.GRAPH),
                style={"height": "87vh"},
            ),
        )
