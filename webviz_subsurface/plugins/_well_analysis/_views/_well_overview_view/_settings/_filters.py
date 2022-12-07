from typing import Dict, List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import EnsembleWellAnalysisData


class WellOverviewFilters(SettingsGroupABC):
    class Ids(StrEnum):
        SELECTED_WELLS = "selected-wells"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:
        super().__init__("Filters")
        self._wells: List[str] = []
        for ens_data_model in data_models.values():
            self._wells.extend(
                [well for well in ens_data_model.wells if well not in self._wells]
            )

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(self._wells)),
                id=self.register_component_unique_id(
                    WellOverviewFilters.Ids.SELECTED_WELLS
                ),
                options=[{"label": well, "value": well} for well in self._wells],
                value=self._wells,
                multi=True,
            )
        ]
