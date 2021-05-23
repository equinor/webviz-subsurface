from typing import Callable

import dash
from dash.dependencies import Input, Output, State, ALL


def layout_controllers(app: dash.Dash, get_uuid: Callable):
    @app.callback(
        Output({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "style"),
        Output(get_uuid("page-selected-inplace-dist"), "data"),
        Input({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "n_clicks"),
        State({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "id"),
    )
    def _update_clicked_button(_apply_click, id_all):
        ctx = dash.callback_context.triggered[0]
        page_selected = id_all[0]["button"]
        styles = []
        for button_id in id_all:
            if button_id["button"] in ctx["prop_id"]:
                styles.append({"background-color": "#7393B3", "color": "#fff"})
                page_selected = button_id["button"]
            else:
                styles.append({"background-color": "#E8E8E8"})
        if ctx["prop_id"] == ".":
            styles[0] = {"background-color": "#7393B3", "color": "#fff"}
        return styles, page_selected

    @app.callback(
        Output({"id": get_uuid("main-inplace-dist"), "page": ALL}, "style"),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
        State({"id": get_uuid("main-inplace-dist"), "page": ALL}, "id"),
    )
    def _select_main_layout(page_selected, all_ids):
        styles = []
        for page_id in all_ids:
            if page_id["page"] == page_selected:
                styles.append({"display": "block"})
            else:
                styles.append({"display": "none"})
        return styles

    @app.callback(
        Output(
            {
                "id": get_uuid("main-inplace-dist"),
                "wrapper": ALL,
                "page": "Custom plotting",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("main-inplace-dist"), "element": "plot-table-select"},
            "value",
        ),
        State(
            {
                "id": get_uuid("main-inplace-dist"),
                "wrapper": ALL,
                "page": "Custom plotting",
            },
            "id",
        ),
    )
    def _show_hide_1x1(plot_table_select, all_ids):
        styles = []
        for input_id in all_ids:
            if input_id["wrapper"] == plot_table_select:
                styles.append({"display": "block"})
            else:
                styles.append({"display": "none"})
        return styles

    @app.callback(
        Output(
            {
                "id": get_uuid("selections-inplace-dist"),
                "element": "table_response_group_wrapper",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "settings": "sync_table"},
            "value",
        ),
    )
    def _show_hide_table_response_group_controls(sync_table):
        return {"display": "none"} if sync_table else {"display": "block"}
