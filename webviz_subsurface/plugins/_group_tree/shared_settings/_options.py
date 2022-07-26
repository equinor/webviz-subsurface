from typing import Dict, List

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._ensemble_group_tree_data import EnsembleGroupTreeData
from .._plugin_ids import PluginIds
from .._types import StatOptions, TreeModeOptions


class Options(SettingsGroupABC):

    OPTIONS_ID = ""
    # pylint: disable=too-few-public-methods
    class Ids:
        OPTIONS = "options"
        STATISTICS = "statistics"
        REALIZATION = "realization"

    def __init__(self, ensembles: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("Options")
        self.ensembles = ensembles

    def layout(self) -> Component:
        return wcc.FlexBox(id=self.register_component_unique_id(Options.Ids.OPTIONS))

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.STATISTICS), "data"),
            Input(
                self.component_unique_id(Options.Ids.STATISTICS).to_string(), "value"
            ),
        )
        def _update_statics_store(selected_options: str) -> str:
            return selected_options

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.REALIZATION), "data"),
            Input(
                self.component_unique_id(Options.Ids.REALIZATION).to_string(), "value"
            ),
        )
        def _update_realization_store(selected_options: List[str]) -> List[str]:
            return selected_options

        @callback(
            Output(
                self.component_unique_id(Options.Ids.OPTIONS).to_string(), "children"
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.REALIZATION), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
        )
        def _update_avaliable_options(
            real_state: int, selected_mode: str, ensemble_name: str
        ) -> list:
            current_element = None
            unique_real = self.ensembles[ensemble_name].get_unique_real()
            if selected_mode == TreeModeOptions.STATISTICS.value:
                current_element = wcc.RadioItems(
                    id=self.register_component_unique_id(Options.Ids.STATISTICS),
                    options=[
                        {"label": "Mean", "value": StatOptions.MEAN.value},
                        {"label": "P10 (high)", "value": StatOptions.P10.value},
                        {"label": "P50 (median)", "value": StatOptions.P50.value},
                        {"label": "P90 (low)", "value": StatOptions.P90.value},
                        {"label": "Maximum", "value": StatOptions.MAX.value},
                        {"label": "Minimum", "value": StatOptions.MIN.value},
                    ],
                    value=StatOptions.MEAN.value,
                )

            else:
                current_element = wcc.Dropdown(
                    label="Realization",
                    id=self.register_component_unique_id(Options.Ids.REALIZATION),
                    options=[{"label": real, "value": real} for real in unique_real],
                    value=real_state if real_state in unique_real else min(unique_real),
                    multi=False,
                )
            return current_element
