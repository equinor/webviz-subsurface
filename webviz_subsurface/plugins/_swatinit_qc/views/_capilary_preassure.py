import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel
from ..settings_groups import CapilarFilters, CapilarSelections
from ..views import CapilarViewelement


class TabMaxPcInfoLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        CAPILAR_TAB = "capilar-tab"
        MAIN_CLOUMN = "main-column"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
        dframe: pd.DataFrame,
        selectors: list,
        map_figure: go.Figure,
    ) -> None:
        super().__init__("Capillary pressure scaling")
        self.datamodel = datamodel
        self.dframe = dframe
        self.selectors = selectors
        self.map_figure = map_figure

        main_column = self.add_column(TabMaxPcInfoLayout.IDs.MAIN_CLOUMN)
        row = main_column.make_row()
        row.add_view_element(
            CapilarViewelement(self.dframe, self.selectors, self.map_figure),
            TabMaxPcInfoLayout.IDs.CAPILAR_TAB,
        )

        self.add_settings_group(CapilarSelections(self.datamodel))
        self.add_settings_group(CapilarFilters(self.datamodel))

    # set callbacks
