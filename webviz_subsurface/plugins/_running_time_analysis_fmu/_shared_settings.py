from typing import List, Tuple, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ._plugin_ids import PluginIds


class RunningTimeAnalysisFmuSettings(SettingsGroupABC):
    
    # pylint: disable=too-few-public-methods
    class Ids:
        MODE = "mode-1"
        ENSEMBLE = "ensemble-1"
        COLORING = "coloring-1"
        FILTERING = "filtering"

    COLOR_MATRIX_BY_LABELS = [
    "Same job in ensemble",
    "Slowest job in realization",
    "Slowest job in ensemble",
    ]
    COLOR_PARCOORD_BY_LABELS = [
    "Successful/failed realization",
    "Running time of realization",
    ]
    def __init__(
        self, ensembles: list, 
        visual_parameters :list, 
        plugin_paratamters:List[str],
        filter_shorter: Union[int, float] = 10
        ) -> None:
        super().__init__("Data filter")
        self.ensembles = ensembles
        self.filter_shorter = filter_shorter
        self.parameters = plugin_paratamters
        self.visual_parameters = visual_parameters

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label = "Mode",
                id = self.register_component_unique_id(self.Ids.MODE),
                options=[
                        {
                            "label": "Running time matrix",
                            "value": "running_time_matrix",
                        },
                        {
                            "label": "Parameter parallel coordinates",
                            "value": "parallel_coordinates",
                        },
                    ],
                value="running_time_matrix",
            ),
            wcc.Dropdown(
                label = "Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[
                    {"label": ens, "value": ens} for ens in self.ensembles
                ],
                value=self.ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Color jobs relative to running time of:",
                id=self.register_component_unique_id(self.Ids.COLORING),
                options=[
                    {"label": rel, "value": rel}
                    for rel in self.COLOR_MATRIX_BY_LABELS
                ],
                value=self.COLOR_MATRIX_BY_LABELS[0],
                clearable=False,
            ),
            wcc.FlexBox(
                id = self.register_component_unique_id(self.Ids.FILTERING),
                children = wcc.Checklist(
                                label="Filtering",
                                id=self.register_component_unique_id("filter_short"),
                                options=[
                                    {
                                        "label": "Slowest in ensemble less than "
                                        f"{self.filter_shorter}s",
                                        "value": "filter_short",
                                    },
                                ],
                                value=["filter_short"],
                            ),
            )
        ]

    def set_callbacks(self) -> None:

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.MODE), 'data'),
            Input(self.component_unique_id(self.Ids.MODE).to_string(), 'value')
        )
        def _update_mode_store(
                selected_mode: str
                ) -> str:
            return selected_mode

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.ENSEMBLE), 'data'),
            Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), 'value')
        )
        def _update_ensemble_store(
                selected_ensemble: str
                ) -> str:
            return selected_ensemble

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.COLORING), 'data'),
            Input(self.component_unique_id(self.Ids.COLORING).to_string(), 'value')
        )
        def _update_coloring_store(
                selected_coloring: str
                ) -> str:
            return selected_coloring

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.FILTERING_SHORT), 'data'),
            Input(self.component_unique_id("filter_short").to_string(), 'value')
        )
        def _update_fshort_store(
                selected_filtering_short: str
                ) -> str:
            return selected_filtering_short

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.FILTERING_PARAMS), 'data'),
            Input(self.component_unique_id("filter_params").to_string(), 'value')
        )
        def _update_fparms_store(
                selected_fparams: str
                ) -> str:
            return selected_fparams

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.REMOVE_CONSTANT), 'data'),
            Input(self.component_unique_id("remove_constant").to_string(), 'value')
        )
        def _update_remove_store(
                selected_remove: str
                ) -> str:
            return selected_remove
            
        @callback(
            Output(self.component_unique_id(self.Ids.FILTERING).to_string(),"children"),
            Output(self.component_unique_id(self.Ids.COLORING).to_string(),'label'),
            Output(self.component_unique_id(self.Ids.COLORING).to_string(),'options'),
            Output(self.component_unique_id(self.Ids.COLORING).to_string(),'value'),
            Input(self.component_unique_id(self.Ids.MODE).to_string(),'value')
        )
        def _update_color(selected_mode: str) -> Tuple:
            children = None
            label = None
            optons = None
            value = None
            if selected_mode == "running_time_matrix":
                children = wcc.Checklist(
                                label="Filtering jobs",
                                id=self.register_component_unique_id("filter_short"),
                                options=[
                                    {
                                        "label": "Slowest in ensemble less than "
                                        f"{self.filter_shorter}s",
                                        "value": "filter_short",
                                    },
                                ],
                                value=["filter_short"],
                            )
                label = "Color jobs relative to running time of:"
                options = [
                            {"label": rel, "value": rel}
                            for rel in self.COLOR_MATRIX_BY_LABELS
                        ]
                value = self.COLOR_MATRIX_BY_LABELS[0]
            else:
                children = [
                            wcc.Checklist(
                                label= "Filtering",
                                id=self.register_component_unique_id("remove_constant"),
                                options=[
                                    {
                                        "label": " Remove constant ",
                                        "value": "remove_constant",
                                    },
                                ],
                                value=[],
                            ),
                            wcc.SelectWithLabel(
                                    id=self.register_component_unique_id("filter_params"),
                                    style={"overflowX": "auto", "fontSize": "0.97rem"},
                                    options=[
                                        {"label": param, "value": param}
                                        for param in self.parameters
                                    ],
                                    multi=True,
                                    value=self.visual_parameters,
                                    size=min(50, len(self.visual_parameters)),
                                )
                                ]
                label = "Color realizations relative to:"
                options = [
                            {"label": rel, "value": rel}
                            for rel in self.COLOR_PARCOORD_BY_LABELS
                        ]
                value = self.COLOR_PARCOORD_BY_LABELS[0]
                
            return (children, label,options,value)


                