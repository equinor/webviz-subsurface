from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config.utils import StrEnum

from .view_elements import TornadoPlot


class TornadoPlotView(ViewABC):
    class IDs(StrEnum):
        TORNADO_PLOT = "tornado-plot"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
    ) -> None:
        super().__init__("Tornado Plot View")

        column = self.add_column(TornadoPlotView.IDs.MAIN_COLUMN)
        first_row = column.make_row()
        first_row.add_view_element(TornadoPlot(), TornadoPlotView.IDs.TORNADO_PLOT)
