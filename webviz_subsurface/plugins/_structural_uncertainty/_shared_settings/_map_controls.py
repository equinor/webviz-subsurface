from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class MapControls(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        #-surface A
        SURFACE_ATTRIBUTE_A = "surface-attribute-a"
        SURFACE_NAME_A = "surface-name-a"
        CALCULATION_REAL_A = "calculation-real-a"
        CALCULATE_WELL_INTER_A = "calculate-well-inter-a"

        #-surface B
        SURFACE_ATTRIBUTE_B = "surface-attribute-b"
        SURFACE_NAME_B = "surface-name-b"
        CALCULATION_REAL_B = "calculation-real-b"
        CALCULATE_WELL_INTER_B = "calculate-well-inter-b"


        #-settings
        AUTO_COMP_DIFF = "auto-comp-diff"
        COLOR_RANGES = "color-ranges"
        SURFACE_A_MIN_MAX = "surface-a-min-max"
        SURFACE_B_MIN_MAX = "surface-b-min-max"
        SYNC_RANGE_ON_MAPS = "sync-range-on-maps"

        #-filter
        REAL_FILTER = "real-filter"


    def __init__(
        
    ) -> None:
        super().__init__("Filter")

        

    def layout(self) -> List[Component]:
        return [
            
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"
            ),
            Input(self.ensemble_id, "value"),
        )
        def _set_ensembles(selected_ensemble: str) -> str:
            return selected_ensemble