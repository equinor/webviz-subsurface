from typing import Callable

import dash
from dash.dependencies import Input, Output, State
import dash_table
import webviz_core_components as wcc

from ..models import ParametersModel


def parameter_qc_controller(
    app: dash.Dash, get_uuid: Callable, parametermodel: ParametersModel
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

        if plot_type == "table":
            columns, dframe = parametermodel.make_statistics_table(
                ensembles=ensembles, parameters=parameters
            )
            return dash_table.DataTable(
                style_table={
                    "height": "75vh",
                    "overflow": "auto",
                    "fontSize": "1.5rem",
                },
                columns=columns,
                data=dframe,
                sort_action="native",
                filter_action="native",
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
        Output(
            {"id": get_uuid("filter-parameter"), "tab": "qc"},
            "options",
        ),
        Output(
            {"id": get_uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
        Input(get_uuid("delta-sort"), "value"),
        Input({"id": get_uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": get_uuid("delta-ensemble-selector"), "tab": "qc"}, "value"),
        State(
            {"id": get_uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
    )
    def _update_parameters(sortby, ensemble, delta_ensemble, current_params):
        """Callback to sort parameters based on selection"""
        parametermodel.sort_parameters(
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            sortby=sortby,
        )
        return [
            {"label": i, "value": i} for i in parametermodel.parameters
        ], current_params
