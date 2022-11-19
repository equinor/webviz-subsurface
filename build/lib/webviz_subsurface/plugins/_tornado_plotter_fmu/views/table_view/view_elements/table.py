from dash import dash_table
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class TornadoTable(ViewElementABC):
    class IDs(StrEnum):
        TABLE = "table"

    def __init__(self, height: str = "75vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> dash_table.DataTable:
        return dash_table.DataTable(
            id=self.register_component_unique_id(TornadoTable.IDs.TABLE),
            style_cell={"whiteSpace": "normal", "height": "auto"},
        )
