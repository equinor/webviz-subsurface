from typing import List, Type

from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC
from webviz_core_components import Graph as WccGraph


class Graph(ViewElementABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        GRAPH = "graph"

    def __init__(
        self, p_cols: List, height: str = "43vh", matrix: bool = False
    ) -> None:
        super().__init__()

        self.height = height
        self.matrix = matrix
        self.p_cols = p_cols

    def inner_layout(self) -> Type[Component]:
        """If the graph is a matrix plot, the parameter "clickData" must be included"""
        if self.matrix:
            return WccGraph(
                id=self.register_component_unique_id(Graph.IDs.GRAPH),
                style={"height": self.height, "min-height": "300px"},
                clickData={"points": [{"x": self.p_cols[0], "y": self.p_cols[0]}]},
            )
        return WccGraph(
            id=self.register_component_unique_id(Graph.IDs.GRAPH),
            style={"height": self.height, "min-height": "300px"},
        )
