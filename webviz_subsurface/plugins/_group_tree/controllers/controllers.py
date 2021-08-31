from typing import Callable, Optional, Any, Tuple, List, Dict
import json
import pandas as pd
import dash
from dash.dependencies import Input, Output, State

import webviz_subsurface_components

from ..utils.utils import (
    create_grouptree_dataset,
    filter_smry,
    get_ensemble_real_options,
)


def controllers(
    app: dash.Dash,
    get_uuid: Callable,
    smry: pd.DataFrame,
    gruptree: pd.DataFrame,
) -> None:
    @app.callback(
        Output({"id": get_uuid("controls"), "element": "realization"}, "options"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "value"),
        Input({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _update_realization_dropdown(
        ensemble_name: str,
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """This callback updates the realization dropdown options"""
        return get_ensemble_real_options(smry, ensemble_name), 0

    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Input({"id": get_uuid("controls"), "element": "mean_or_single_real"}, "value"),
        Input({"id": get_uuid("controls"), "element": "realization"}, "value"),
        State({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _render_grouptree(
        mean_or_single_real: str, real: int, ensemble_name: str
    ) -> list:
        """This callback updates the input dataset to the Grouptree component."""
        if mean_or_single_real == "plot_mean":
            smry_ens = filter_smry(smry, ensemble_name)
        elif mean_or_single_real == "single_real":
            smry_ens = filter_smry(smry, ensemble_name, real)
        else:
            raise ValueError(f"Not valid option :{mean_or_single_real}")

        data = json.load(
            create_grouptree_dataset(
                smry_ens,
                gruptree[gruptree.ENSEMBLE == ensemble_name],
            )
        )
        return [
            webviz_subsurface_components.GroupTree(id="grouptree", data=data),
        ]

    @app.callback(
        Output(
            {"id": get_uuid("controls"), "element": "single_real_options"},
            "style",
        ),
        Input(
            {"id": get_uuid("controls"), "element": "mean_or_single_real"},
            "value",
        ),
    )
    def _show_hide_single_real_options(mean_or_single_real: str) -> Dict:
        if mean_or_single_real == "plot_mean":
            return {"display": "none"}
        return {"display": "block"}
