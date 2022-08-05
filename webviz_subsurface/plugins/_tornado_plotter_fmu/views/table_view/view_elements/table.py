from dash import dash_table
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class TornadoTable(ViewElementABC):
    """View element for table"""

    class IDs:
        # pylint: disable=too-few-public-methods
        TABLE = "table"

    def __init__(self, height: str = "75vh") -> None:
        super().__init__()
        self.height = height

    def inner_layout(self) -> dash_table.DataTable:
        return dash_table.DataTable(
            id=self.register_component_unique_id(TornadoTable.IDs.TABLE),
            style_cell={"whiteSpace": "normal", "height": "auto"},
        )
