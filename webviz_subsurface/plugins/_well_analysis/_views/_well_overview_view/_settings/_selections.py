import datetime
from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class WellOverviewSelections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLES = "ensembles"
        RESPONSE = "response"
        PROD_FROM_DATE = "prod-from-date"
        PROD_UNTIL_DATE = "prod-until-date"

    def __init__(self, ensembles: List[str], dates: List[datetime.datetime]) -> None:
        super().__init__("Selections")

        self._ensembles = ensembles
        self._dates = dates

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
                label="Production From Date",
                id=self.register_component_unique_id(self.Ids.PROD_FROM_DATE),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self._dates
                ],
                multi=False,
            ),
            wcc.Dropdown(
                label="Production Until Date",
                id=self.register_component_unique_id(self.Ids.PROD_UNTIL_DATE),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self._dates
                ],
                multi=False,
            ),
        ]
