from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class PlotPicker(SettingsGroupABC):
    """Settingsgroup for switching between table and bar view"""

    class IDs:
        # pylint: disable=too-few-public-methods
        BARS_OR_TABLE = "bars-or-table"

    def __init__(self) -> None:
        super().__init__("Visualization type")

        self.picker_options = [
            {"label": "Show bars", "value": "bars"},
            {"label": "Show table", "value": "table"},
        ]

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(PlotPicker.IDs.BARS_OR_TABLE),
                options=self.picker_options,
                value="bars",
                inline=True,
            )
        ]
