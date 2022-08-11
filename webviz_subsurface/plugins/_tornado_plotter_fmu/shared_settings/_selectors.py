import re
from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIDs


class Selectors(SettingsGroupABC):
    """Settings class for labelled dropdown with all response columns"""

    class IDs:
        # pylint: disable=too-few-public-methods
        RESPONSE = "response"

    def __init__(
        self,
        responses: List[str],
        initial_response: str,
    ) -> None:
        super().__init__("Selectors")
        self._responses = responses
        self._initial_response = initial_response

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.RESPONSE),
                label="Response",
                options=[{"label": i, "value": i} for i in self._responses],
                value=self._initial_response,
                multi=False,
                clearable=False,
            )
        ]
