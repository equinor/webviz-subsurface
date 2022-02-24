from typing import Callable, Optional

from dash import MATCH, Dash, Input, Output, State
from dash.exceptions import PreventUpdate


def open_dialogs(
    app: Dash,
    get_uuid: Callable,
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("dialog"), "dialog_id": MATCH, "element": "wrapper"},
            "open",
        ),
        Input(
            {"id": get_uuid("dialog"), "dialog_id": MATCH, "element": "button-open"},
            "n_clicks",
        ),
        State(
            {"id": get_uuid("dialog"), "dialog_id": MATCH, "element": "wrapper"},
            "open",
        ),
    )
    def _toggle_dialog_graph_settings(n_open: int, is_open: bool) -> Optional[bool]:
        """Open or close graph settings dialog button"""
        if n_open:
            return not is_open
        raise PreventUpdate
