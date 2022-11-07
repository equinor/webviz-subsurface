from typing import Any, Dict, List, Tuple

from dash import Input, Output, State, callback
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._types import VfpParam
from ..._utils import VfpDataModel, VfpTable
from ._settings import Filters, Selections, Vizualisation
from ._utils import VfpFigureBuilder
from ._view_element import VfpViewElement


class VfpView(ViewABC):
    class Ids(StrEnum):
        VIEW_ELEMENT = "view-element"
        SELECTIONS = "selections"
        FILTERS = "filters"
        VIZUALISATION = "vizualisation"

    def __init__(self, data_model: VfpDataModel) -> None:
        super().__init__("VFP Analysis")

        self._data_model = data_model

        self.add_settings_group(
            Selections(self._data_model.vfp_names), VfpView.Ids.SELECTIONS
        )
        self.add_settings_group(
            Vizualisation(self._data_model.vfp_names), VfpView.Ids.VIZUALISATION
        )
        self.add_settings_group(Filters(), VfpView.Ids.FILTERS)

        self.add_view_element(VfpViewElement(), VfpView.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            # Options
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.THP),
                "options",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.WFR),
                "options",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.GFR),
                "options",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.ALQ),
                "options",
            ),
            # Values
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.THP),
                "value",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.WFR),
                "value",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.GFR),
                "value",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.ALQ),
                "value",
            ),
            # Labels
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.THP_LABEL),
                "children",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.WFR_LABEL),
                "children",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.GFR_LABEL),
                "children",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.ALQ_LABEL),
                "children",
            ),
            # Input
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VFP_NAME
                ),
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

            thp_dict = vfp_table.params[VfpParam.THP]
            wfr_dict = vfp_table.params[VfpParam.WFR]
            gfr_dict = vfp_table.params[VfpParam.GFR]
            alq_dict = vfp_table.params[VfpParam.ALQ]

            return (
                [{"label": value, "value": idx} for idx, value in thp_dict.items()],
                [{"label": value, "value": idx} for idx, value in wfr_dict.items()],
                [{"label": value, "value": idx} for idx, value in gfr_dict.items()],
                [{"label": value, "value": idx} for idx, value in alq_dict.items()],
                list(thp_dict.keys()),
                [list(wfr_dict.keys())[0]],
                [list(gfr_dict.keys())[0]],
                [list(alq_dict.keys())[0]],
                f"THP = {vfp_table.param_types[VfpParam.THP].name}",
                f"WFR = {vfp_table.param_types[VfpParam.WFR].name}",
                f"GFR = {vfp_table.param_types[VfpParam.GFR].name}",
                f"ALQ = {vfp_table.param_types[VfpParam.ALQ].name}",
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
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, Vizualisation.Ids.COLOR_BY
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VFP_NAME
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_vfp_graph(
            thps: List[int],
            wfrs: List[int],
            gfrs: List[int],
            alqs: List[int],
            color_by: VfpParam,
            vfp_name: str,
        ) -> Dict[str, Any]:
            # pylint: disable=too-many-locals
            vfp_table = self._data_model.get_vfp_table(vfp_name)

            figure_builder = VfpFigureBuilder(vfp_name=vfp_name)

            selected_indices = {
                VfpParam.THP: thps,
                VfpParam.WFR: wfrs,
                VfpParam.GFR: gfrs,
                VfpParam.ALQ: alqs,
            }
            selected_color_by_values = vfp_table.get_values(
                color_by, selected_indices[color_by]
            )
            cmax = max(selected_color_by_values)
            cmin = min(selected_color_by_values)

            for thp_idx in thps:
                for wfr_idx in wfrs:
                    for gfr_idx in gfrs:
                        for alq_idx in alqs:
                            figure_builder.add_vfp_curve(
                                rates=vfp_table.rate_values,
                                bhp_values=vfp_table.get_bhp_series(
                                    thp_idx, wfr_idx, gfr_idx, alq_idx
                                ),
                                cmax=cmax,
                                cmin=cmin,
                                vfp_table=vfp_table,
                                indices={
                                    VfpParam.THP: thp_idx,
                                    VfpParam.WFR: wfr_idx,
                                    VfpParam.GFR: gfr_idx,
                                    VfpParam.ALQ: alq_idx,
                                },
                                color_by=color_by,
                            )

            return figure_builder.get_figure()
