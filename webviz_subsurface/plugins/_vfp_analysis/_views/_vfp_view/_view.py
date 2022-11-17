from typing import Any, Dict, List, Tuple

from dash import Input, Output, State, callback, dcc
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._types import PressureType, VfpParam
from ..._utils import VfpDataModel, VfpTable
from ._settings import Filters, PressureOption, Selections, Vizualisation
from ._utils import VfpFigureBuilder
from ._view_elements import VfpGraph


class VfpView(ViewABC):
    class Ids(StrEnum):
        VFP_GRAPH = "vfp-graph"
        VFP_METADATA = "vfp-metadata"
        SELECTIONS = "selections"
        PRESSURE_OPTION = "pressure-option"
        VIZUALISATION = "vizualisation"
        FILTERS = "filters"

    def __init__(self, data_model: VfpDataModel) -> None:
        super().__init__("VFP Analysis")

        self._data_model = data_model

        self.add_settings_group(
            Selections(self._data_model.vfp_names), VfpView.Ids.SELECTIONS
        )
        self.add_settings_group(PressureOption(), VfpView.Ids.PRESSURE_OPTION)
        self.add_settings_group(
            Vizualisation(self._data_model.vfp_names), VfpView.Ids.VIZUALISATION
        )
        self.add_settings_group(Filters(), VfpView.Ids.FILTERS)
        column = self.add_column()
        column.add_view_element(VfpGraph(), VfpView.Ids.VFP_GRAPH)
        # column.add_view_element(VfpMetadata(), VfpView.Ids.VFP_METADATA)

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
            # Size of filter boxes
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.THP),
                "size",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.WFR),
                "size",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.GFR),
                "size",
            ),
            Output(
                self.settings_group_unique_id(self.Ids.FILTERS, Filters.Ids.ALQ),
                "size",
            ),
            # Table metadata
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.METADATA_DIALOG
                ),
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
        @callback_typecheck
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
            int,
            int,
            int,
            int,
            dcc.Markdown,
        ]:
            """Updates the filter values, sets the initial selection, and
            updates the filter label.
            """
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
                f"THP: {vfp_table.param_types[VfpParam.THP].name}",
                f"WFR: {vfp_table.param_types[VfpParam.WFR].name}",
                f"GFR: {vfp_table.param_types[VfpParam.GFR].name}",
                f"ALQ: {vfp_table.param_types[VfpParam.ALQ].name}",
                min(6, len(thp_dict)),
                min(6, len(wfr_dict)),
                min(6, len(gfr_dict)),
                min(6, len(alq_dict)),
                dcc.Markdown(vfp_table.get_metadata_markdown()),
            )

        @callback(
            # Options
            Output(
                self.view_element_unique_id(self.Ids.VFP_GRAPH, VfpGraph.Ids.GRAPH),
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
            Input(
                self.settings_group_unique_id(
                    self.Ids.PRESSURE_OPTION, PressureOption.Ids.PRESSURE_OPTION
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
            pressure_type: PressureType,
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
            showscale = True
            for thp_idx in thps:
                for wfr_idx in wfrs:
                    for gfr_idx in gfrs:
                        for alq_idx in alqs:
                            figure_builder.add_vfp_curve(
                                rates=vfp_table.get_values(vfp_param=VfpParam.RATE),
                                bhp_values=vfp_table.get_bhp_series(
                                    pressure_type, thp_idx, wfr_idx, gfr_idx, alq_idx
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
                                showscale=showscale,
                            )
                            if showscale:
                                showscale = False

            figure_builder.set_xaxis_settings(title=vfp_table.get_rate_label())
            figure_builder.set_yaxis_settings(
                title=vfp_table.get_bhp_label(pressure_type=pressure_type)
            )

            return figure_builder.get_figure()
