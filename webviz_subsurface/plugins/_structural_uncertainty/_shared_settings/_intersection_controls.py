from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from intersection_data import intersection_data_layout
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class IntersectionControls(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        #intersection controls
        X_LINE = "x-line"
        Y_LINE = "y-line"
        STEP = "step"
        WELL = "well"
        SURFACE_ATTR = "surface-attr"
        SURFACE_NAMES = "surface-names"
        SHOW_SURFACES = "show-surfaces"
        UPDATE_INTERSECTION = "update-intersection"
        UNCERTAINTY_TABLE = "uncertainty-table"

        #-settings
        RESOLUTION = "resolution"
        EXTENSION = "extension"
        DEPTH_RANGE = "depth-range"
        TRUNKATE_LOCK = "trunkate-lock"
        KEEP_ZOOM = "keep-zoom"
        INTERSECTION_COLORS = "intersection-colors"



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



