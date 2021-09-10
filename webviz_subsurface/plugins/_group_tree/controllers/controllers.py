from typing import Callable, Optional, Any, Tuple, List, Dict
import json
import pandas as pd
import dash
from dash.dependencies import Input, Output, State

import webviz_subsurface_components

from ..group_tree_data import GroupTreeData


def controllers(
    app: dash.Dash, get_uuid: Callable, grouptreedata: GroupTreeData
) -> None:
    @app.callback(
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "options"),
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "options"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "value"),
        Input({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _update_ensemble_options(
        ensemble: str,
    ) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]], Optional[int]]:
        """Updates the selection options when the ensemble value changes"""

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

        if not grouptreedata.tree_is_equivalent_in_all_real(ensemble):
            tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
            tree_mode_options[0]["disabled"] = True
            tree_mode_value = "single_real"

        real_options, real_default = grouptreedata.get_ensemble_real_options(ensemble)

        return (
            tree_mode_options,
            tree_mode_value,
            real_options,
            real_default,
        )

    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Input({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Input({"id": get_uuid("controls"), "element": "realization"}, "value"),
        State({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _render_grouptree(tree_mode: str, real: int, ensemble: str) -> list:
        """This callback updates the input dataset to the Grouptree component."""
        return [
            webviz_subsurface_components.GroupTree(
                id="grouptree",
                data=grouptreedata.create_grouptree_dataset(ensemble, tree_mode, real),
            ),
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
