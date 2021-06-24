from typing import Callable, Tuple

import dash
from dash.dependencies import Input, Output, State, ALL


def layout_controllers(app: dash.Dash, get_uuid: Callable) -> None:
    @app.callback(
        Output({"id": get_uuid("selections"), "button": ALL}, "style"),
        Output(get_uuid("page-selected"), "data"),
        Output({"id": get_uuid("main-voldist"), "page": ALL}, "style"),
        Output(get_uuid("voldist-page-selected"), "data"),
        Input({"id": get_uuid("selections"), "button": ALL}, "n_clicks"),
        Input(get_uuid("tabs"), "value"),
        State({"id": get_uuid("selections"), "button": ALL}, "id"),
        State({"id": get_uuid("main-voldist"), "page": ALL}, "id"),
        State(get_uuid("voldist-page-selected"), "data"),
    )
    def _selected_page_controllers(
        _apply_click: int,
        tab_selected: str,
        button_ids: dict,
        main_layout_ids: list,
        prev_voldist_page: str,
    ) -> Tuple[list, str, list, str]:

        ctx = dash.callback_context.triggered[0]

        if (
            tab_selected != "voldist"
            or "tabs" in ctx["prop_id"]
            and prev_voldist_page is not None
        ):
            return (
                [dash.no_update] * len(button_ids),
                tab_selected if tab_selected != "voldist" else prev_voldist_page,
                [dash.no_update] * len(main_layout_ids),
                dash.no_update,
            )

        button_styles = []
        for button_id in button_ids:
            if button_id["button"] in ctx["prop_id"]:
                button_styles.append({"background-color": "#7393B3", "color": "#fff"})
                page_selected = button_id["button"]
            else:
                button_styles.append({"background-color": "#E8E8E8"})
        if (
            ctx["prop_id"] == "."
            or "tabs" in ctx["prop_id"]
            and prev_voldist_page is None
        ):
            page_selected = button_ids[0]["button"]
            button_styles[0] = {"background-color": "#7393B3", "color": "#fff"}

        voldist_layout = []
        for page_id in main_layout_ids:
            if page_id["page"] == page_selected:
                voldist_layout.append({"display": "block"})
            else:
                voldist_layout.append({"display": "none"})

        return button_styles, page_selected, voldist_layout, page_selected

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
                "id": get_uuid("selections"),
                "tab": "voldist",
                "element": "table_response_group_wrapper",
            },
            "style",
        ),
        Input(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": "sync_table"},
            "value",
        ),
    )
    def _show_hide_table_response_group_controls(sync_table: list) -> dict:
        return {"display": "none"} if sync_table else {"display": "block"}
