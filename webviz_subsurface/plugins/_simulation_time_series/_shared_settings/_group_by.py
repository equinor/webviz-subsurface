from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds
from ..types import SubplotGroupByOptions


class GroupBySettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS = "subplot-owner-options-radio-items"

    def __init__(self) -> None:
        super().__init__("Group by")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    self.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ),
                options=[
                    {
                        "label": "Time Series",
                        "value": SubplotGroupByOptions.VECTOR.value,
                    },
                    {
                        "label": "Ensemble",
                        "value": SubplotGroupByOptions.ENSEMBLE.value,
                    },
                ],
                value=SubplotGroupByOptions.VECTOR.value,
            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def _update_store_group_by(selected_data: str) -> str:
            return selected_data
