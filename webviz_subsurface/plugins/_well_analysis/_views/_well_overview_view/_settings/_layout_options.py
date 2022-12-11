from typing import List

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import ChartType


class WellOverviewLayoutOptions(SettingsGroupABC):
    class Ids(StrEnum):
        CHARTTYPE_SETTINGS = "charttype-settings"
        CHARTTYPE_CHECKLIST = "charttype-checklist"

    def __init__(self) -> None:
        super().__init__("Layout Options")

    def layout(self) -> List[Component]:
        settings_id = self.register_component_unique_id(self.Ids.CHARTTYPE_SETTINGS)
        checklist_id = self.register_component_unique_id(self.Ids.CHARTTYPE_CHECKLIST)
        return [
            html.Div(
                children=[
                    html.Div(
                        id={"id": settings_id, "charttype": ChartType.BAR},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.BAR},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {"label": "Overlay bars", "value": "overlay_bars"},
                                {
                                    "label": "Show prod as text",
                                    "value": "show_prod_text",
                                },
                                {
                                    "label": "White background",
                                    "value": "white_background",
                                },
                            ],
                            value=["legend"],
                        ),
                    ),
                    html.Div(
                        id={"id": settings_id, "charttype": ChartType.PIE},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.PIE},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {
                                    "label": "Show prod as text",
                                    "value": "show_prod_text",
                                },
                            ],
                            value=[],
                        ),
                    ),
                    html.Div(
                        id={"id": settings_id, "charttype": ChartType.AREA},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.AREA},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {
                                    "label": "White background",
                                    "value": "white_background",
                                },
                            ],
                            value=["legend"],
                        ),
                    ),
                ],
            ),
        ]
