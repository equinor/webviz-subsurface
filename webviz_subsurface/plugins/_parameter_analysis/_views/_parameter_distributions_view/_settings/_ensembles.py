from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ParamDistEnsembles(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE_A = "ensemble-a"
        ENSEMBLE_B = "ensemble-b"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Ensembles")
        if not ensembles:
            raise ValueError("List of ensembles can't be empty.")
        self._ensembles = ensembles

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble A:",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE_A),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                multi=False,
                value=self._ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Ensemble B:",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE_B),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                multi=False,
                value=self._ensembles[-1],
                clearable=False,
            ),
        ]
