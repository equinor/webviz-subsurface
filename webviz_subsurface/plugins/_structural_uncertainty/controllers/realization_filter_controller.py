from typing import Callable, Dict, List, Optional, Tuple

from dash import Dash, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate


def update_realizations(app: Dash, get_uuid: Callable) -> None:
    @app.callback(
        Output(
            {
                "id": get_uuid("dialog"),
                "dialog_id": "realization-filter",
                "element": "apply",
            },
            "disabled",
        ),
        Output(
            {
                "id": get_uuid("dialog"),
                "dialog_id": "realization-filter",
                "element": "apply",
            },
            "style",
        ),
        Input(
            get_uuid("realization-store"),
            "data",
        ),
        Input(
            {"id": get_uuid("intersection-data"), "element": "realizations"},
            "value",
        ),
    )
    def _activate_realization_apply_btn(
        stored_reals: List, selected_reals: List
    ) -> Tuple[bool, Dict[str, str]]:
        if stored_reals is None or selected_reals is None:
            raise PreventUpdate
        if set(stored_reals) == set(selected_reals):
            return True, {"visibility": "hidden"}
        return False, {"visibility": "visible"}

    @app.callback(
        Output(
            get_uuid("realization-store"),
            "data",
        ),
        Input(
            {
                "id": get_uuid("dialog"),
                "dialog_id": "realization-filter",
                "element": "apply",
            },
            "n_clicks",
        ),
        State(
            {"id": get_uuid("intersection-data"), "element": "realizations"},
            "value",
        ),
    )
    def _store_realizations(btn_click: Optional[int], selected_reals: List) -> List:
        if btn_click:
            return selected_reals
        raise PreventUpdate

    @app.callback(
        Output(
            {"id": get_uuid("intersection-data"), "element": "realizations"},
            "value",
        ),
        Input(
            {
                "id": get_uuid("dialog"),
                "dialog_id": "realization-filter",
                "element": "clear",
            },
            "n_clicks",
        ),
        Input(
            {
                "id": get_uuid("dialog"),
                "dialog_id": "realization-filter",
                "element": "all",
            },
            "n_clicks",
        ),
        State(
            {"id": get_uuid("intersection-data"), "element": "realizations"},
            "options",
        ),
    )
    def _update_realization_list(
        clear_click: Optional[int], all_click: Optional[int], real_opts: List
    ) -> List:
        if clear_click is None and all_click is None:
            raise PreventUpdate
        ctx = callback_context.triggered
        if "clear" in ctx[0]["prop_id"]:
            return []
        if "all" in ctx[0]["prop_id"]:
            return [opt["value"] for opt in real_opts]
        raise PreventUpdate
