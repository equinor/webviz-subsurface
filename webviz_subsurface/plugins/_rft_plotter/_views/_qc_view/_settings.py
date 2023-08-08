from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class QCSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        COLUMNS = "columns"
        ONLY_INACTIVE = "only-inactive"

    def __init__(self, ensembles: List[str], columns: List[str]) -> None:
        super().__init__("Settings")
        self._ensembles = ensembles
        self._columns = columns
        self._default_columns = [
            "REAL",
            "EAST",
            "NORTH",
            "MD",
            "ZONE",
            "WELL",
            "DATE",
            "VALID_ZONE",
            "ACTIVE",
            "INACTIVE_INFO",
        ]
        self._default_columns = [
            col for col in self._default_columns if col in self._columns
        ]

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
            wcc.SelectWithLabel(
                label="Columns",
                size=min(10, len(self._columns)),
                id=self.register_component_unique_id(self.Ids.COLUMNS),
                options=[{"label": name, "value": name} for name in self._columns],
                value=self._default_columns,
                multi=True,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(self.Ids.ONLY_INACTIVE),
                options=[
                    {
                        "label": "View only inactive",
                        "value": "only_inactive",
                    }
                ],
                value=[],
            ),
        ]
