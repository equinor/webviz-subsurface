from typing import Callable, Optional

from dash import MATCH, Dash, Input, Output, State
from dash.exceptions import PreventUpdate


def open_modals(
    app: Dash,
    get_uuid: Callable,
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("modal"), "modal_id": MATCH, "element": "wrapper"},
            "is_open",
        ),
        Input(
            {"id": get_uuid("modal"), "modal_id": MATCH, "element": "button-open"},
            "n_clicks",
        ),
        State(
            {"id": get_uuid("modal"), "modal_id": MATCH, "element": "wrapper"},
            "is_open",
        ),
    )
    def _toggle_modal_graph_settings(n_open: int, is_open: bool) -> Optional[bool]:
        """Open or close graph settings modal button"""
        if n_open:
            return not is_open
        raise PreventUpdate
