from typing import Callable, Optional, Any, Tuple, List, Dict
import json
import pandas as pd
import dash
from dash.dependencies import Input, Output, State

import webviz_subsurface_components

from ..utils.utils import (
    create_grouptree_dataset,
    filter_smry,
    filter_gruptree,
    get_ensemble_real_options,
)


def controllers(
    app: dash.Dash,
    get_uuid: Callable,
    smry: pd.DataFrame,
    gruptree: pd.DataFrame,
) -> None:
    @app.callback(
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "options"),
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "options"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "value"),
        Input({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _update_ensemble_options(
        ensemble_name: str,
    ) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]], Optional[int]]:
        """Updates the selection options when the ensemble value changes"""

        gruptree_ens = gruptree[gruptree["ENSEMBLE"] == ensemble_name]
        tree_mode_options: List[Dict[str, Any]] = [
            {
                "label": "Ensemble mean",
                "value": "plot_mean",
            },
            {
                "label": "Single realization",
                "value": "single_real",
            },
        ]
        tree_mode_value = "plot_mean"

        if len(gruptree_ens["REAL"].unique()) != 1:
            tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
            tree_mode_options[0]["disabled"] = True
            tree_mode_value = "single_real"

        return (
            tree_mode_options,
            tree_mode_value,
            get_ensemble_real_options(smry, ensemble_name),
            0,
        )

    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Input({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Input({"id": get_uuid("controls"), "element": "realization"}, "value"),
        State({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _render_grouptree(tree_mode: str, real: int, ensemble_name: str) -> list:
        """This callback updates the input dataset to the Grouptree component."""
        if tree_mode == "plot_mean":
            smry_ens = filter_smry(smry, ensemble_name)
            gruptree_ens = filter_gruptree(gruptree, ensemble_name)
        elif tree_mode == "single_real":
            smry_ens = filter_smry(smry, ensemble_name, real)
            gruptree_ens = filter_gruptree(gruptree, ensemble_name, real)
        else:
            raise ValueError(f"Not valid option :{tree_mode}")

        data = json.load(
            create_grouptree_dataset(
                smry_ens,
                gruptree_ens,
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
            {"id": get_uuid("controls"), "element": "tree_mode"},
            "value",
        ),
    )
    def _show_hide_single_real_options(tree_mode: str) -> Dict:
        if tree_mode == "plot_mean":
            return {"display": "none"}
        return {"display": "block"}
