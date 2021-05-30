from typing import Callable, Tuple

import dash
from dash.dependencies import Input, Output, State, ALL


def layout_controllers(app: dash.Dash, get_uuid: Callable) -> None:
    @app.callback(
        Output({"id": get_uuid("selections-voldist"), "button": ALL}, "style"),
        Output(get_uuid("page-selected-voldist"), "data"),
        Input({"id": get_uuid("selections-voldist"), "button": ALL}, "n_clicks"),
        State({"id": get_uuid("selections-voldist"), "button": ALL}, "id"),
    )
    def _update_clicked_button(_apply_click: int, all_ids: dict) -> Tuple[list, str]:
        ctx = dash.callback_context.triggered[0]
        page_selected = all_ids[0]["button"]
        styles = []
        for button_id in all_ids:
            if button_id["button"] in ctx["prop_id"]:
                styles.append({"background-color": "#7393B3", "color": "#fff"})
                page_selected = button_id["button"]
            else:
                styles.append({"background-color": "#E8E8E8"})
        if ctx["prop_id"] == ".":
            styles[0] = {"background-color": "#7393B3", "color": "#fff"}
        return styles, page_selected

    @app.callback(
        Output({"id": get_uuid("main-voldist"), "page": ALL}, "style"),
        Input(get_uuid("page-selected-voldist"), "data"),
        State({"id": get_uuid("main-voldist"), "page": ALL}, "id"),
    )
    def _select_main_layout(page_selected: str, all_ids: dict) -> list:
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
                "id": get_uuid("main-voldist"),
                "wrapper": ALL,
                "page": "custom",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        State(
            {
                "id": get_uuid("main-voldist"),
                "wrapper": ALL,
                "page": "custom",
            },
            "id",
        ),
    )
    def _show_hide_1x1(plot_table_select: str, all_ids: dict) -> list:
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
                "id": get_uuid("selections-voldist"),
                "element": "table_response_group_wrapper",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("selections-voldist"), "selector": "sync_table"}, "value"
        ),
    )
    def _show_hide_table_response_group_controls(sync_table: list) -> dict:
        return {"display": "none"} if sync_table else {"display": "block"}
