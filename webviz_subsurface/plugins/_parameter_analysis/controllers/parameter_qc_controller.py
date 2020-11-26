from dash.dependencies import Input, Output, State
import dash_table
import webviz_core_components as wcc


def parameter_qc_controller(parent, app):
    @app.callback(
        Output(parent.uuid("property-qc-wrapper"), "children"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": parent.uuid("delta-ensemble-selector"), "tab": "qc"}, "value"),
        Input(
            {"id": parent.uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
        Input(parent.uuid("property-qc-plot-type"), "value"),
    )
    def _update_bars(ensemble, delta_ensemble, parameters, plot_type):
        """Callback to switch visualization between table and distribution plots"""
        parameters = parameters if isinstance(parameters, list) else [parameters]
        ensembles = [ensemble, delta_ensemble]

        if plot_type == "table":
            columns, dframe = parent.pmodel.make_statistics_table(
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
            id=parent.uuid("property-qc-graph"),
            config={"displayModeBar": False},
            style={"height": "75vh"},
            figure=parent.pmodel.make_grouped_plot(
                ensembles=ensembles,
                parameters=parameters,
                plot_type=plot_type,
            ),
        )

    @app.callback(
        Output(
            {"id": parent.uuid("filter-parameter"), "tab": "qc"},
            "options",
        ),
        Output(
            {"id": parent.uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
        Input(parent.uuid("delta-sort"), "value"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": parent.uuid("delta-ensemble-selector"), "tab": "qc"}, "value"),
        State(
            {"id": parent.uuid("filter-parameter"), "tab": "qc"},
            "value",
        ),
    )
    def _update_parameters(sortby, ensemble, delta_ensemble, current_params):
        """Callback to sort parameters based on selection"""
        parent.pmodel.sort_parameters(
            ensemble=ensemble,
            delta_ensemble=delta_ensemble,
            sortby=sortby,
        )
        return [
            {"label": i, "value": i} for i in parent.pmodel.parameters
        ], current_params
