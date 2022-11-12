from dash import dcc, html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class VfpMetadata(ViewElementABC):
    class Ids(StrEnum):
        GRAPH = "graph"

    def __init__(self) -> None:
        super().__init__()

    def _metadata_text(self) -> str:
        return f"""
> **Metadata**
> - **VFP type** VFPPROD

        """

    def inner_layout(self) -> html.Div:
        return html.Div(children=dcc.Markdown(self._metadata_text()))
