from typing import Type, List, Dict

from dash import callback, Input, Output
from dash.exceptions import PreventUpdate
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_Ids import PluginIds
from .._types import TreeModeOptions, StatOptions
from .._ensemble_group_tree_data import EnsembleGroupTreeData
from ._control import Controls

class Options(SettingsGroupABC):

    OPTIONS_ID=""

    class Ids:
        OPTIONS = "options"
        STATISTICS = "statistics"
        REALIZATION = "realization"


    def __init__(self, ensembles: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("Options")
        self.ensembles = ensembles
        self.options_id = self.register_component_unique_id (self.Ids.OPTIONS)
        self.statistic_id = self.register_component_unique_id (self.Ids.STATISTICS)
        self.realization_id = self.register_component_unique_id (self.Ids.REALIZATION)

    def layout(self) -> Component:
        
        return wcc.FlexBox(
            id = self.register_component_unique_id(Options.Ids.OPTIONS)
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.STATISTICS), "data"),
            Input(self.component_unique_id(Options.Ids.STATISTICS).to_string(), "value"),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data")
        )
        def _update_statics_store (selected_options: str, selected_mode: str) -> str:
            #if selected_mode == TreeModeOptions.STATISTICS.value:
                return selected_options
            #else: 
            #    raise PreventUpdate

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.REALIZATION), "data"),
            Input(self.component_unique_id(Options.Ids.REALIZATION).to_string(), "value"),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data")
        )
        def _update_realization_store (selected_options: List[str], selected_mode: str) ->List[str]:
            #if selected_mode == TreeModeOptions.SINGLE_REAL.value:
                return selected_options
            #else: 
             #   raise PreventUpdate

        @callback(
            Output(self.component_unique_id(Options.Ids.OPTIONS).to_string(), 'children'),
            # Output(self.component_unique_id(Options.Ids.STATISTICS).to_string(), 'style'),
            # Output(self.component_unique_id(Options.Ids.REALIZATION).to_string(), 'style'),
            # Output(self.component_unique_id(Options.Ids.REALIZATION).to_string(), 'options'),
            # Output(self.component_unique_id(Options.Ids.REALIZATION).to_string(), 'value'),
            Input(self.get_store_unique_id(PluginIds.Stores.REALIZATION), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
        )
        def _update_avaliable_options (real_state: int, selected_mode: str, ensemble_name: str) -> list:
            unique_real = self.ensembles[ensemble_name].get_unique_real()
            if selected_mode == TreeModeOptions.STATISTICS.value:
                return wcc.RadioItems(
                                id = self.register_component_unique_id(Options.Ids.STATISTICS),
                                options=[
                                    {"label": "Mean", "value": StatOptions.MEAN.value},
                                    {"label": "P10 (high)", "value": StatOptions.P10.value},
                                    {"label": "P50 (median)", "value": StatOptions.P50.value},
                                    {"label": "P90 (low)", "value": StatOptions.P90.value},
                                    {"label": "Maximum", "value": StatOptions.MAX.value},
                                    {"label": "Minimum", "value": StatOptions.MIN.value},
                                ],
                                value = StatOptions.MEAN.value
                            ),
            else:
                return wcc.Dropdown(
                        label="Realization",
                        id= self.register_component_unique_id (Options.Ids.REALIZATION),
                        options=[{"label": real, "value": real} for real in unique_real],
                        value= real_state if real_state in unique_real else min(unique_real),
                        multi=False
                    )