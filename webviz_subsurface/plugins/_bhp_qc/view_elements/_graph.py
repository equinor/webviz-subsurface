from typing import Type

from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC
from webviz_core_components import Graph as WccGraph


class Graph(ViewElementABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        GRAPH = "graph"

    def __init__(self, height: str = "65vh") -> None:
        super().__init__()

        self.height = height

    def inner_layout(self) -> Type[Component]:
        return WccGraph(
            id=self.register_component_unique_id(Graph.Ids.GRAPH),
            style={"height": self.height, "min-height": "300px"},
        )
