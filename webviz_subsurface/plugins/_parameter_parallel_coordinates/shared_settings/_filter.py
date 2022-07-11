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
        EXCLUDE_INCLUDE = "exclude-include"
        PARAMETERS = "parameters"
        ACTIVE_VIEW = "active-view"

    def __init__(
        self,
        parallel_df: pd.DataFrame,
        ensembles: List[str],
        parameter_columns: List[str],
    ) -> None:
        super().__init__("Filter")

        self.parallel_df = parallel_df
        self.ensembles = ensembles
        self.parameter_columns = parameter_columns

    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                label="Ensembles",
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                value=self.ensembles,
            ),
            wcc.Selectors(
                label="Parameter filter",
                children=[
                    wcc.RadioItems(
                        id=self.register_component_unique_id(
                            Filter.Ids.EXCLUDE_INCLUDE
                        ),
                        options=[
                            {"label": "Exclude", "value": "exc"},
                            {"label": "Include", "value": "inc"},
                        ],
                        value="exc",
                    ),
                    wcc.SelectWithLabel(
                        label="Parameters",
                        id=self.register_component_unique_id(Filter.Ids.PARAMETERS),
                        options=[
                            {"label": ens, "value": ens}
                            for ens in self.parameter_columns
                        ],
                        multi=True,
                        size=min(len(self.parameter_columns), 15),
                        value=[],
                    ),
                ],
            ),
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

        @callback(
            Output(self.get_store_unique_id(Filter.Ids.ACTIVE_VIEW), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.ACTIVE_VIEW), "data"),
        )
        def _scream_ensembles(active_view: str) -> str:
            print(active_view)
            return active_view

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_EXCLUDE_INCLUDE),
                "data",
            ),
            Input(
                self.component_unique_id(Filter.Ids.EXCLUDE_INCLUDE).to_string(),
                "value",
            ),
        )
        def _set_ensembles(selected_excl_incl: str) -> str:
            return selected_excl_incl

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_PARAMETERS), "data"
            ),
            Input(self.component_unique_id(Filter.Ids.PARAMETERS).to_string(), "value"),
        )
        def _set_ensembles(selected_parameters: str) -> str:
            return selected_parameters
