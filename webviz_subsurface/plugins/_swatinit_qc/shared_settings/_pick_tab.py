from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs


class PickTab(SettingsGroupABC):
    class IDs:
        # pylint: diable=too-few-public-methods
        TAB_PICKER = "tab-picker"

    def __init__(self) -> None:
        super().__init__("Pick Tab")
        self.tab_options = [
            {"label": "Overview and Information", "value": "info"},
            {"label": "Water Initalization QC plots", "value": "water"},
            {"label": "Capillart preassure scaling", "value": "capilar"},
        ]

    def layout(self) -> Component:
        return wcc.RadioItems(
            id=self.register_component_unique_id(PickTab.IDs.TAB_PICKER),
            options=self.tab_options,
            value="info",
            inline=False,
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Shared.PICK_VIEW),
                "data",
            ),
            Input(
                self.component_unique_id(PickTab.IDs.TAB_PICKER).to_string(),
                "value",
            ),
        )
        def _set_tab(tab: str) -> str:
            return tab
