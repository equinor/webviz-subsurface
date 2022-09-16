from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config.utils import StrEnum

from .view_elements import TornadoTable


class TornadoTableView(ViewABC):

    class IDs(StrEnum):
        TORNADO_TABLE = "tornado-table"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
    ) -> None:
        super().__init__("Table View")

        column = self.add_column(TornadoTableView.IDs.MAIN_COLUMN)
        first_row = column.make_row()
        first_row.add_view_element(TornadoTable(), TornadoTableView.IDs.TORNADO_TABLE)
