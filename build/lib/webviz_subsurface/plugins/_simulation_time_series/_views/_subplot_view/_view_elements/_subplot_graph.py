import webviz_core_components as wcc
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class SubplotGraph(ViewElementABC):
    """View element for subplot graph"""

    class Ids(StrEnum):
        GRAPH = "graph"

    def __init__(self, height: str = "86vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> wcc.Graph:
        return wcc.Graph(
            style={"display": "block", "height": self.height},
            id=self.register_component_unique_id(SubplotGraph.Ids.GRAPH),
        )
