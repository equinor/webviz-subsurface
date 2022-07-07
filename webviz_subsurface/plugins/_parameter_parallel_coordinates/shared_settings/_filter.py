from typing import Dict, List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        ENSEMBLE = "ensemble"
        WELLS = "wells"
        MAX_NUMBER_OF_WELLS_SLIDER = "max-number-of-wells-slider"
        SORT_BY = "sort-by"
        ASCENDING_DESCENDING = "ascending-descending"

    def __init__(self, bhp_df: pd.DataFrame) -> None:
        super().__init__("Filter")

        self.bhp_df = bhp_df

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLE),
                options=[{"label": i, "value": i} for i in self.ensembles],
                value=self.ensembles[0],
                clearable=False,
                multi=False,
            )
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"
            ),
            Input(self.component_unique_id(Filter.Ids.ENSEMBLE).to_string(), "value"),
        )
        def _set_ensembles(selected_ensemble: str) -> str:
            return selected_ensemble
