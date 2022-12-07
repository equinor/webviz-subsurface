import datetime
from typing import Dict, List, Set

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import EnsembleWellAnalysisData


class WellOverviewSelections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLES = "ensembles"
        RESPONSE = "response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:
        super().__init__("Selections")

        self._ensembles = list(data_models.keys())

        dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            dates = dates.union(ens_data_model.dates)
        self._sorted_dates: List[datetime.datetime] = sorted(list(dates))

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(self.Ids.ENSEMBLES),
                options=[{"label": col, "value": col} for col in self._ensembles],
                value=self._ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(self.Ids.RESPONSE),
                options=[
                    {"label": "Oil production", "value": "WOPT"},
                    {"label": "Gas production", "value": "WGPT"},
                    {"label": "Water production", "value": "WWPT"},
                ],
                value="WOPT",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Only Production after date",
                id=self.register_component_unique_id(
                    self.Ids.ONLY_PRODUCTION_AFTER_DATE
                ),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self._sorted_dates
                ],
                multi=False,
            ),
        ]
