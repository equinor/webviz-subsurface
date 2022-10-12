from typing import Any, List

import webviz_core_components as wcc
from dash import html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Filters(SettingsGroupABC):
    class Ids(StrEnum):
        THP_LABEL = "thp-label"
        WFR_LABEL = "wfr-label"
        GFR_LABEL = "gfr-label"
        ALQ_LABEL = "alq-label"
        THP = "thp"
        WFR = "wfr"
        GFR = "gfr"
        ALQ = "alq"

    def __init__(self) -> None:
        super().__init__("Filters")

    def layout(self) -> List[Any]:
        return [
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.THP_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.THP),
                size=6,
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.WFR_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.WFR),
                size=6,
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.GFR_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.GFR),
                size=6,
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.ALQ_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.ALQ),
                size=6,
            ),
        ]
