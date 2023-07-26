from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class QCSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Settings")
        self._ensembles = ensembles

    def layout(self) -> List[Component]:
        ensemble = self._ensembles[0] if self._ensembles else None
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=ensemble,
                multi=False,
                clearable=False,
            ),
        ]
