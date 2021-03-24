from typing import Optional, List, Callable, Union

import dash
from dash.dependencies import Input, Output, State


def set_single_real_mode(app: dash.Dash, get_uuid: Callable):
    @app.callback(
        Output(
            {
                "id": get_uuid("clientside"),
                "attribute": "single_real",
            },
            "data",
        ),
        Output(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "multi",
        ),
        Output(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "value",
        ),
        Output(get_uuid("traces"), "options"),
        Output(get_uuid("traces"), "value"),
        Input(get_uuid("single_real_mode"), "value"),
        State(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "value",
        ),
        prevent_initial_call=True,
    )
    def _set_realization_mode(
        single_real_mode: Optional[List], current_ensemble: Union[List, str]
    ):
        traceopts = [{"label": "Realizations", "value": "Realizations"}]
        if single_real_mode:
            for label in ["Mean", "P10/P90", "Low/High"]:
                traceopts.append({"label": label, "value": label, "disabled": True})
            return True, False, current_ensemble[0], traceopts, ["Realizations"]
        for label in ["Mean", "P10/P90", "Low/High"]:
            traceopts.append({"label": label, "value": label})
        return False, True, [current_ensemble], traceopts, ["Realizations"]
