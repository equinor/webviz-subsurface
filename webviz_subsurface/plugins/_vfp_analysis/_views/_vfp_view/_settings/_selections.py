from typing import Any, List

import webviz_core_components as wcc
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        VFP_NAME = "vfp-name"

    def __init__(self, vfp_names: List[str]) -> None:
        super().__init__("Selections")
        self._vfp_names = vfp_names

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Selections.Ids.VFP_NAME),
                label="VFP name",
                options=[{"label": vfp, "value": vfp} for vfp in self._vfp_names],
                clearable=False,
                value=self._vfp_names[0] if len(self._vfp_names) > 0 else None,
                persistence=True,
                persistence_type="session",
            )
        ]
