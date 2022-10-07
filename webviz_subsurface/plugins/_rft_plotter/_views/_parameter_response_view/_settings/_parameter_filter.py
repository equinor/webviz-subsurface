from typing import List

import pandas as pd
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ......_components.parameter_filter import ParameterFilter


class ParameterFilterSettings(SettingsGroupABC):
    class Ids(StrEnum):
        PARAM_FILTER = "param-filter"

    def __init__(self, parameter_df: pd.DataFrame, mc_ensembles: List[str]) -> None:
        super().__init__("Parameter Filter")
        self._parameter_df = parameter_df
        self._mc_ensembles = mc_ensembles

    def layout(self) -> List[Component]:
        return ParameterFilter(
            uuid=self.register_component_unique_id(self.Ids.PARAM_FILTER),
            dframe=self._parameter_df[
                self._parameter_df["ENSEMBLE"].isin(self._mc_ensembles)
            ].copy(),
            reset_on_ensemble_update=True,
            display_header=False,
        ).layout
