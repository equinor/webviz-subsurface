from typing import Any, Dict, List, Tuple

from dash import Input, Output, State, callback
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._utils import VfpDataModel, VfpTable
from ._settings import Filters, Settings
from ._utils import VfpFigureBuilder
from ._view_element import VfpViewElement


class VfpView(ViewABC):
    class Ids(StrEnum):
        VIEW_ELEMENT = "view-element"
        SETTINGS = "settings"
        FILTERS = "filters"

    def __init__(self, data_model: VfpDataModel) -> None:
        super().__init__("VFP Analysis")

        self._data_model = data_model

        self.add_settings_group(
            Settings(self._data_model.vfp_names), VfpView.Ids.SETTINGS
        )
        self.add_settings_group(Filters(), VfpView.Ids.FILTERS)

        self.add_view_element(VfpViewElement(), VfpView.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            # Options
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.THP)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ)
                .to_string(),
                "options",
            ),
            # Values
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.THP)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ)
                .to_string(),
                "value",
            ),
            # Labels
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.THP_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ_LABEL)
                .to_string(),
                "children",
            ),
            # Input
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(Settings.Ids.VFP_NAME)
                .to_string(),
                "value",
            ),
        )
        def _update_filters(
            vfp_name: str,
        ) -> Tuple[
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[float],
            List[float],
            List[float],
            List[float],
            str,
            str,
            str,
            str,
        ]:

            vfp_table: VfpTable = self._data_model.get_vfp_table(vfp_name)

            thp_dict = vfp_table.thp_dict
            wfr_dict = vfp_table.wfr_dict
            gfr_dict = vfp_table.gfr_dict
            alq_dict = vfp_table.alq_dict

            return (
                [{"label": value, "value": idx} for idx, value in thp_dict.items()],
                [{"label": value, "value": idx} for idx, value in wfr_dict.items()],
                [{"label": value, "value": idx} for idx, value in gfr_dict.items()],
                [{"label": value, "value": idx} for idx, value in alq_dict.items()],
                list(thp_dict.keys()),
                list(wfr_dict.keys()),
                list(gfr_dict.keys()),
                list(alq_dict.keys()),
                vfp_table.thp_type,
                vfp_table.wfr_type,
                vfp_table.gfr_type,
                vfp_table.alq_type,
            )

        @callback(
            # Options
            Output(
                self.view_element_unique_id(
                    self.Ids.VIEW_ELEMENT, VfpViewElement.Ids.GRAPH
                ),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.THP),
                "value",
            ),
            Input(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.WFR),
                "value",
            ),
            Input(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.GFR),
                "value",
            ),
            Input(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.ALQ),
                "value",
            ),
            State(
                self.settings_group_unique_id(self.Ids.SETTINGS, Settings.Ids.VFP_NAME),
                "value",
            ),
        )
        def _update_vfp_graph(
            thps: List[int],
            wfrs: List[int],
            gfrs: List[int],
            alqs: List[int],
            vfp_name: str,
        ) -> Dict[str, Any]:
            vfp_table = self._data_model.get_vfp_table(vfp_name)

            figure_builder = VfpFigureBuilder()

            for thp_idx in thps:
                for wfr_idx in wfrs:
                    for gfr_idx in gfrs:
                        for alq_idx in alqs:
                            figure_builder.add_vfp_curve(
                                vfp_table.rate_values,
                                vfp_table.get_bhp_series(
                                    thp_idx, wfr_idx, gfr_idx, alq_idx
                                ),
                            )

            return figure_builder.get_serialized_figure()
