import webviz_core_components as wcc
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class TornadoPlot(ViewElementABC):
    class IDs(StrEnum):
        GRAPH = "graph"

    def __init__(self, height: str = "86vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> wcc.Graph:
        return wcc.Graph(
            id=self.register_component_unique_id(TornadoPlot.IDs.GRAPH),
            config={"displayModeBar": True},
            style={"display": "block", "height": self.height},
        )
