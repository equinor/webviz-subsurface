import plotly.graph_objects as go
from dash import Input, Output, State, callback
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel
from ..settings_groups import WaterFilters, WaterSelections
from ..view_elements import WaterViewelement


class TabQqPlotLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        WATER_TAB = "water-tab"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
        main_figure: go.Figure,
        map_figure: go.Figure,
        qc_volumes: dict,
    ) -> None:
        super().__init__("Water Initialization QC plots")
        self.datamodel = datamodel
        self.main_figure = main_figure
        self.map_figure = map_figure
        self.qc_volumes = qc_volumes

        main_column = self.add_column(TabQqPlotLayout.IDs.MAIN_COLUMN)
        row = main_column.make_row()
        row.add_view_element(
            WaterViewelement(
                self.datamodel, self.main_figure, self.map_figure, self.qc_volumes
            ),
            TabQqPlotLayout.IDs.WATER_TAB,
        )

        self.add_settings_group(WaterSelections(self.datamodel))
        self.add_settings_group(WaterFilters(self.datamodel))

    # set callbacks
