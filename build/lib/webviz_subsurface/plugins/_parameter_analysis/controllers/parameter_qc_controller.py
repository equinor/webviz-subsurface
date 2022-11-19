from typing import Callable

import webviz_core_components as wcc
from dash import Dash, Input, Output, State, dash_table

from ..models import ParametersModel


def parameter_qc_controller(
    app: Dash, get_uuid: Callable, parametermodel: ParametersModel
):
    @app.callback(
        Output(get_uuid("property-qc-wrapper"), "children"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": get_uuid("delta-ensemble-selector"), "tab": "qc"}, "value"),
        Input(
            {"id": get_uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
        Input(get_uuid("property-qc-plot-type"), "value"),
    )
    def _update_bars(ensemble, delta_ensemble, parameters, plot_type):
        """Callback to switch visualization between table and distribution plots"""
        parameters = parameters if isinstance(parameters, list) else [parameters]
        ensembles = [ensemble, delta_ensemble]
        valid_params = parametermodel.pmodel.get_parameters_for_ensembles(ensembles)
        parameters = [x for x in parameters if x in valid_params]

        if plot_type == "table":
            columns, dframe = parametermodel.make_statistics_table(
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
            id=get_uuid("property-qc-graph"),
            config={"displayModeBar": False},
            style={"height": "75vh"},
            figure=parametermodel.make_grouped_plot(
                ensembles=ensembles,
                parameters=parameters,
                plot_type=plot_type,
            ),
        )

    @app.callback(
        Output({"id": get_uuid("filter-parameter"), "tab": "qc"}, "options"),
        Output({"id": get_uuid("filter-parameter"), "tab": "qc"}, "value"),
        Input(get_uuid("delta-sort"), "value"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": get_uuid("delta-ensemble-selector"), "tab": "qc"}, "value"),
        State({"id": get_uuid("filter-parameter"), "tab": "qc"}, "value"),
    )
    def _update_parameters(sortby, ensemble, delta_ensemble, current_params):
        """Callback to sort parameters based on selection"""
        parametermodel.sort_parameters(
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            sortby=sortby,
        )
        valid_params = parametermodel.pmodel.get_parameters_for_ensembles(
            [ensemble, delta_ensemble]
        )
        sorted_params = [x for x in parametermodel.parameters if x in valid_params]
        return (
            [{"label": i, "value": i} for i in sorted_params],
            [x for x in current_params if x in sorted_params],
        )
