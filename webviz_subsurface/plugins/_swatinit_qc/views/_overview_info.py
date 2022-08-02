import webviz_core_components as wcc
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from .._swatint import SwatinitQcDataModel
from ..view_elements import OverviewViewelement


class OverviewTabLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        OVERVIEW_TAB = "overview-tab"
        MAIN_CLOUMN = "main-column"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__("Overview and Information")
        self.datamodel = datamodel

        main_column = self.add_column(OverviewTabLayout.IDs.MAIN_CLOUMN)
        row = main_column.make_row()
        row.add_view_element(
            OverviewViewelement(self.datamodel), OverviewTabLayout.IDs.OVERVIEW_TAB
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(OverviewTabLayout.IDs.OVERVIEW_TAB)
                .component_unique_id(OverviewViewelement.IDs.INFO_DIALOG)
                .to_string(),
                "open",
            ),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Overview.BUTTON), "data"),
            State(
                self.view_element(OverviewTabLayout.IDs.OVERVIEW_TAB)
                .component_unique_id(OverviewViewelement.IDs.INFO_DIALOG)
                .to_string(),
                "open",
            ),
        )
        def open_close_information_dialog(_n_click: list, is_open: bool) -> bool:
            if _n_click is not None:
                return not is_open
            raise PreventUpdate
