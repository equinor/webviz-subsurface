from typing import Any, Dict, List

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds
from .._types import TreeModeOptions


class Controls(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        CONTROLS = "controls"
        ENSEMBLE = "ensemble"
        TREEMODE = "tree-mode"

    def __init__(self, ensembles: list) -> None:
        super().__init__("Controls")

        self.ensembles = ensembles

        self.tree_mode_options: List[Dict[str, Any]] = [
            {
                "label": "Statistics",
                "value": TreeModeOptions.STATISTICS.value,
            },
            {
                "label": "Single realization",
                "value": TreeModeOptions.SINGLE_REAL.value,
            },
        ]

    def layout(self) -> Component:
        return wcc.FlexBox(
            id=self.register_component_unique_id(self.Ids.CONTROLS),
            children=[
                wcc.Dropdown(
                    id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                    label="Ensemble",
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    clearable=False,
                    value=self.ensembles[0],
                ),
                wcc.RadioItems(
                    id=self.register_component_unique_id(self.Ids.TREEMODE),
                    label="Statistics or realization",
                    options=self.tree_mode_options,
                    value=self.tree_mode_options[1]["value"],
                ),
            ],
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data"),
            Input(self.component_unique_id(Controls.Ids.TREEMODE).to_string(), "value"),
        )
        def _update_treemode_atore(selected_mode: str) -> str:
            return selected_mode

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
            Input(self.component_unique_id(Controls.Ids.ENSEMBLE).to_string(), "value"),
        )
        def _update_ensembles_store(selected_mode: str) -> str:
            return selected_mode
