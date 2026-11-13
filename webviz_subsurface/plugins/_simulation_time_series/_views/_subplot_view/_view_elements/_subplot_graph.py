import webviz_core_components as wcc
from dash import dcc, html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class SubplotGraph(ViewElementABC):
    """View element for subplot graph"""

    class Ids(StrEnum):
        GRAPH = "graph"
        DOWNLOAD_SIGNATURE_STORE = "download-signature-store"

    def __init__(self, height: str = "86vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> html.Div:  # type: ignore[override]
        return html.Div(
            children=[
                wcc.Graph(
                    style={"display": "block", "height": self.height},
                    id=self.register_component_unique_id(SubplotGraph.Ids.GRAPH),
                ),
                dcc.Store(
                    id=self.register_component_unique_id(
                        SubplotGraph.Ids.DOWNLOAD_SIGNATURE_STORE
                    ),
                ),
            ],
        )
