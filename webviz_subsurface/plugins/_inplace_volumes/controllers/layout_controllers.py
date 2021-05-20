from typing import Callable

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate


def layout_controllers(app: dash.Dash, get_uuid: Callable):
    @app.callback(
        Output({"id": get_uuid("main-inplace-dist"), "layout": "1x1"}, "style"),
        Output({"id": get_uuid("main-inplace-dist"), "layout": "2x1"}, "style"),
        Input({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "n_clicks"),
    )
    def _select_main_layout(_n_click):
        ctx = dash.callback_context.triggered[0]
        if "Custom plotting" not in ctx["prop_id"]:
            return {"display": "none", "height": "91vh"}, {"display": "block"}
        return {"display": "block", "height": "91vh"}, {"display": "none"}

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "table-wrapper",
                "layout": "1x1",
            },
            "style",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "element": "graph-wrapper",
                "layout": "1x1",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("main-inplace-dist"), "element": "plot-table-select"},
            "value",
        ),
    )
    def _show_hide_1x1(plot_table_select):
        if plot_table_select == "table":
            return {"display": "inline"}, {"display": "none"}
        return {"display": "none"}, {"display": "inline"}

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "wrapper": ALL,
                "layout": "2x1",
            },
            "style",
        ),
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "wrapper": ALL,
                "layout": "2x1_per",
            },
            "style",
        ),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _show_hide_2x1(page_selected):
        if page_selected == "1 plot / 1 table":
            return ([{"display": "block"}] * 2, [{"display": "none"}] * 2)
        return ([{"display": "none"}] * 2, [{"display": "block"}] * 2)
