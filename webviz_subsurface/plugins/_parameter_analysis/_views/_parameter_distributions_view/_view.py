from typing import Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback, dash_table
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._types import VisualizationType
from ..._utils import ParametersModel
from ._settings import (
    ParamDistEnsembles,
    ParamDistParameters,
    ParamDistVisualizationType,
)
from ._view_element import ParamDistViewElement


class ParameterDistributionView(ViewABC):
    class Ids(StrEnum):
        VISUALIZATION_TYPE = "visualization-type"
        ENSEMBLES = "ensembles"
        PARAMETERS = "parameters"
        VIEW_ELEMENT = "view-element"

    def __init__(
        self,
        parametermodel: ParametersModel,
    ) -> None:
        super().__init__("Parameter Distributions")

        self._parametermodel = parametermodel

        self.add_settings_groups(
            {
                self.Ids.VISUALIZATION_TYPE: ParamDistVisualizationType(),
                self.Ids.ENSEMBLES: ParamDistEnsembles(self._parametermodel.ensembles),
                self.Ids.PARAMETERS: ParamDistParameters(
                    self._parametermodel.parameters
                ),
            }
        )

        main_column = self.add_column()
        main_column.add_view_element(ParamDistViewElement(), self.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(self.Ids.VIEW_ELEMENT)
                .component_unique_id(ParamDistViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.ENSEMBLES, ParamDistEnsembles.Ids.ENSEMBLE_A
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.ENSEMBLES, ParamDistEnsembles.Ids.ENSEMBLE_B
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.PARAMETERS, ParamDistParameters.Ids.PARAMETERS
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VISUALIZATION_TYPE,
                    ParamDistVisualizationType.Ids.VISUALIZATION_TYPE,
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_bars(
            ensemble: str,
            delta_ensemble: str,
            parameters: List[str],
            plot_type: VisualizationType,
        ) -> Union[dash_table.DataTable, wcc.Graph]:
            """Callback to switch visualization between table and distribution plots"""
            ensembles = [ensemble, delta_ensemble]
            valid_params = self._parametermodel.pmodel.get_parameters_for_ensembles(
                ensembles
            )
            parameters = [x for x in parameters if x in valid_params]

            if plot_type == VisualizationType.STAT_TABLE:
                columns, dframe = self._parametermodel.make_statistics_table(
                    ensembles=ensembles, parameters=parameters
                )
                return dash_table.DataTable(
                    style_table={
                        "height": "75vh",
                        "overflow": "auto",
                        "fontSize": 15,
                    },
                    style_cell={"textAlign": "center"},
                    style_cell_conditional=[
                        {"if": {"column_id": "PARAMETER|"}, "textAlign": "left"}
                    ],
                    columns=columns,
                    data=dframe,
                    sort_action="native",
                    filter_action="native",
                    merge_duplicate_headers=True,
                )
            return wcc.Graph(
                config={"displayModeBar": False},
                style={"height": "87vh"},
                figure=self._parametermodel.make_grouped_plot(
                    ensembles=ensembles,
                    parameters=parameters,
                    plot_type=plot_type.value,
                ),
            )

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.PARAMETERS, ParamDistParameters.Ids.PARAMETERS
                ),
                "options",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.PARAMETERS, ParamDistParameters.Ids.PARAMETERS
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.PARAMETERS, ParamDistParameters.Ids.SORT_BY
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.ENSEMBLES, ParamDistEnsembles.Ids.ENSEMBLE_A
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.ENSEMBLES, ParamDistEnsembles.Ids.ENSEMBLE_B
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.PARAMETERS, ParamDistParameters.Ids.PARAMETERS
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_parameters(
            sortby: str, ensemble: str, delta_ensemble: str, current_params: List[str]
        ) -> Tuple[List[Dict[str, str]], List[str]]:
            """Callback to sort parameters based on selection"""
            self._parametermodel.sort_parameters(
                ensemble=ensemble,
                delta_ensemble=delta_ensemble,
                sortby=sortby,
            )
            valid_params = self._parametermodel.pmodel.get_parameters_for_ensembles(
                [ensemble, delta_ensemble]
            )
            sorted_params = [
                x for x in self._parametermodel.parameters if x in valid_params
            ]
            return (
                [{"label": i, "value": i} for i in sorted_params],
                [x for x in current_params if x in sorted_params],
            )
