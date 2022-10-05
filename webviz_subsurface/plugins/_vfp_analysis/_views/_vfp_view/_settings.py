from typing import Any, List

import webviz_core_components as wcc
from dash import html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Settings(SettingsGroupABC):
    class Ids(StrEnum):
        VFP_NAME = "vfp-name"

    def __init__(self, vfp_names: List[str]) -> None:
        super().__init__("Settings")
        self._vfp_names = vfp_names

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Settings.Ids.VFP_NAME),
                label="VFP number",
                options=[{"label": vfp, "value": vfp} for vfp in self._vfp_names],
                clearable=False,
                value=self._vfp_names[0] if len(self._vfp_names) > 0 else None,
                persistence=True,
                persistence_type="session",
            )
        ]


# class Filters(SettingsGroupABC):
#     class Ids(StrEnum):
#         RATE_LABEL = "rate-label"
#         PRESSURE_LABEL = "pressure-label"
#         WFR_LABEL = "wfr-label"
#         GFR_LABEL = "gfr-label"
#         ALQ_LABEL = "alq-label"
#         RATE = "RATE"
#         PRESSURE = "pressure"
#         WFR = "wfr"
#         GFR = "gfr"
#         ALQ = "alq"

#     def __init__(self) -> None:
#         super().__init__("Filters")

#     def layout(self) -> List[Any]:
#         return [
#             html.Label(
#                 id=self.register_component_unique_id(Filters.Ids.RATE_LABEL),
#             ),
#             wcc.SelectWithLabel(
#                 id=self.register_component_unique_id(Filters.Ids.RATE),
#             ),
#             html.Label(
#                 id=self.register_component_unique_id(Filters.Ids.PRESSURE_LABEL),
#             ),
#             wcc.SelectWithLabel(
#                 id=self.register_component_unique_id(Filters.Ids.PRESSURE),
#             ),
#             html.Label(
#                 id=self.register_component_unique_id(Filters.Ids.WFR_LABEL),
#             ),
#             wcc.SelectWithLabel(
#                 id=self.register_component_unique_id(Filters.Ids.WFR),
#             ),
#             html.Label(
#                 id=self.register_component_unique_id(Filters.Ids.GFR_LABEL),
#             ),
#             wcc.SelectWithLabel(id=self.register_component_unique_id(Filters.Ids.GFR)),
#             html.Label(
#                 id=self.register_component_unique_id(Filters.Ids.ALQ_LABEL),
#             ),
#             wcc.SelectWithLabel(
#                 id=self.register_component_unique_id(Filters.Ids.ALQ),
#             ),
#         ]
