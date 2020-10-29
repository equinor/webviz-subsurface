from dash.dependencies import Input, Output, ALL
import dash_table
import webviz_core_components as wcc


def property_qc_controller(parent, app):
    @app.callback(
        Output(parent.uuid("property-qc-wrapper"), "children"),
        Input({"id": parent.uuid("ensemble-selector"), "tab": "qc"}, "value"),
        Input({"id": parent.uuid("property-selector"), "tab": "qc"}, "value"),
        Input(
            {"id": parent.uuid("filter-selector"), "tab": "qc", "selector": ALL},
            "value",
        ),
        Input(parent.uuid("property-qc-plot-type"), "value"),
    )
    def _update_bars(ensembles, prop, selectors, plot_type):
        ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
        if plot_type == "table":
            columns, dframe = parent.pmodel.make_statistics_table(
                prop=prop, ensembles=ensembles, selector_values=selectors
            )
            return dash_table.DataTable(
                style_table={
                    "height": "75vh",
                    "overflow": "auto",
                    "fontSize": "1rem",
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
                prop=prop,
                ensembles=ensembles,
                selector_values=selectors,
                plot_type=plot_type,
            ),
        )
