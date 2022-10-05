from typing import Dict, List, Tuple

from dash import Input, Output, callback
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._utils import VfpDataModel, VfpTable
from ._settings import Settings
from ._view_element import VfpViewElement


class VfpView(ViewABC):
    class Ids(StrEnum):
        VIEW_ELEMENT = "view-element"
        SETTINGS = "settings"
        FILTERS = "filters"

    def __init__(self) -> None:
        super().__init__("VFP Analysis")

        #self._data_model = data_model

        # self.add_settings_group(
        #     Settings(self._data_model.vfp_names), VfpView.Ids.SETTINGS
        # )
        #self.add_settings_group(Filters(), VfpView.Ids.FILTERS)

        self.add_view_element(VfpViewElement(), VfpView.Ids.VIEW_ELEMENT)

    # def set_callbacks(self) -> None:
    #     @callback(
    #         # Options
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.RATE)
    #             .to_string(),
    #             "options",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.PRESSURE)
    #             .to_string(),
    #             "options",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.WFR)
    #             .to_string(),
    #             "options",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.GFR)
    #             .to_string(),
    #             "options",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.ALQ)
    #             .to_string(),
    #             "options",
    #         ),
    #         # Values
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.RATE)
    #             .to_string(),
    #             "value",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.PRESSURE)
    #             .to_string(),
    #             "value",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.WFR)
    #             .to_string(),
    #             "value",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.GFR)
    #             .to_string(),
    #             "value",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.ALQ)
    #             .to_string(),
    #             "value",
    #         ),
    #         # Labels
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.RATE_LABEL)
    #             .to_string(),
    #             "children",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.PRESSURE_LABEL)
    #             .to_string(),
    #             "children",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.WFR_LABEL)
    #             .to_string(),
    #             "children",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.GFR_LABEL)
    #             .to_string(),
    #             "children",
    #         ),
    #         Output(
    #             self.settings_group(self.Ids.FILTERS)
    #             .component_unique_id(Filters.Ids.ALQ_LABEL)
    #             .to_string(),
    #             "children",
    #         ),
    #         # Input
    #         Input(
    #             self.settings_group(self.Ids.SETTINGS)
    #             .component_unique_id(Settings.Ids.VFP_NAME)
    #             .to_string(),
    #             "value",
    #         ),
    #     )
    #     def _update_filters(
    #         vfp_name: str,
    #     ) -> Tuple[
    #         List[Dict[str, float]],
    #         List[Dict[str, float]],
    #         List[Dict[str, float]],
    #         List[Dict[str, float]],
    #         List[Dict[str, float]],
    #         List[float],
    #         List[float],
    #         List[float],
    #         List[float],
    #         List[float],
    #         str,
    #         str,
    #         str,
    #         str,
    #         str,
    #     ]:

    #         vfp_table: VfpTable = self._data_model.get_vfp_table(vfp_name)

    #         rate_values = vfp_table.rate_values
    #         thp_values = vfp_table.thp_values
    #         wfr_values = vfp_table.wfr_values
    #         gfr_values = vfp_table.gfr_values
    #         alq_values = vfp_table.alq_values

    #         return (
    #             [{"label": value, "value": value} for value in rate_values],
    #             [{"label": value, "value": value} for value in thp_values],
    #             [{"label": value, "value": value} for value in wfr_values],
    #             [{"label": value, "value": value} for value in gfr_values],
    #             [{"label": value, "value": value} for value in alq_values],
    #             rate_values,
    #             thp_values,
    #             wfr_values,
    #             gfr_values,
    #             alq_values,
    #             vfp_table.rate_type,
    #             vfp_table.thp_type,
    #             vfp_table.wfr_type,
    #             vfp_table.gfr_type,
    #             vfp_table.alq_type,
    #         )
