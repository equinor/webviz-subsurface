from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLES = "ensembles"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Selections")
        self._ensembles = ensembles

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(self.Ids.ENSEMBLES),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=[self._ensembles[0] if len(self._ensembles) > 0 else None],
                clearable=False,
                multi=True,
            ),
        ]
