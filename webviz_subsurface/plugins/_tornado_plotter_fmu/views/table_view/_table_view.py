from pathlib import Path

from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_plugin_subclasses import ViewABC

import webviz_subsurface

from .view_elements import TornadoTable


class TornadoTableView(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        TORNADO_TABLE = "tornado-table"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
    ) -> None:
        super().__init__("Table View")

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "clientside_functions.js"
        )

        viewcolumn = self.add_column(TornadoTableView.IDs.MAIN_COLUMN)
        first_row = viewcolumn.make_row()
        first_row.add_view_element(TornadoTable(), TornadoTableView.IDs.TORNADO_TABLE)
