from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs


class PlotPicker(SettingsGroupABC):
    """Settingsgruop for switching between table and bar view"""

    class IDs:
        # pylint: disable=too-few-public-methods
        BARS_OR_TABLE = "bars-or-table"

    def __init__(self) -> None:
        super().__init__("Vizualisation type")

        self.plicker_options = [
            {"label": "Show bars", "value": "bars"},
            {"label": "Show table", "value": "table"},
        ]

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(PlotPicker.IDs.BARS_OR_TABLE),
                options=self.plicker_options,
                value="bars",
                inline=True,
            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.PlotPicker.BARS_OR_TABLE),
                "data",
            ),
            Input(
                self.component_unique_id(PlotPicker.IDs.BARS_OR_TABLE).to_string(),
                "value",
            ),
        )
        def _set_plotpicker(pick: str) -> str:
            return pick
