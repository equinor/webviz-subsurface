from typing import List

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import StatType


class WellOverviewStatisticalOptions(SettingsGroupABC):
    class Ids(StrEnum):
        STATISTICS = "statistics"

    def __init__(self) -> None:
        super().__init__("Statistics")

    def layout(self) -> List[Component]:
        return [
            html.Div(
                children=[
                    wcc.RadioItems(
                        id=self.register_component_unique_id(self.Ids.STATISTICS),
                        options=[
                            {"label": "Mean", "value": StatType.MEAN},
                            {"label": "P10 (high)", "value": StatType.P10},
                            {
                                "label": "P50 (median)",
                                "value": StatType.P50,
                            },
                            {"label": "P90 (low)", "value": StatType.P90},
                            {"label": "Maximum", "value": StatType.MAX},
                            {"label": "Minimum", "value": StatType.MIN},
                            {"label": "P10 - P90", "value": StatType.P10_MINUS_P90},
                        ],
                        value=StatType.MEAN,
                    )
                ],
            )
        ]
