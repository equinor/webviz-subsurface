from typing import Any, List

import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._business_logic import VfpDataModel
from ..view_elements import VfpViewElement


class ViewSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        VFP_NUMBER = "vfp-number"

    def __init__(self, vfp_numbers: List[int]) -> None:
        super().__init__("Settings")
        self._vfp_numbers = vfp_numbers

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.Ids.VFP_NUMBER),
                label="VFP number",
                options=[{"label": vfp, "value": vfp} for vfp in self._vfp_numbers],
                clearable=False,
                value=self._vfp_numbers[0],
                persistence=True,
                persistence_type="session",
            )
        ]


class VfpView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        VIEW_ELEMENT = "view-element"
        SETTINGS = "settings"

    def __init__(self, data_model: VfpDataModel) -> None:
        super().__init__("VFP Analysis")

        self._data_model = data_model

        self.add_settings_group(
            ViewSettings(self._data_model.get_vfp_numbers()), VfpView.Ids.SETTINGS
        )

        column = self.add_column()
        column.add_view_element(VfpViewElement(), VfpView.Ids.VIEW_ELEMENT)
