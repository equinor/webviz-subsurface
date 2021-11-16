from typing import Any, Callable, Dict, List, Optional, Tuple

import dash
import webviz_subsurface_components
from dash.dependencies import Input, Output, State

from ..group_tree_data import GroupTreeData


def controllers(
    app: dash.Dash, get_uuid: Callable, grouptreedata: GroupTreeData
) -> None:
    @app.callback(
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "options"),
        Output({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Output({"id": get_uuid("options"), "element": "statistical_option"}, "value"),
        Output({"id": get_uuid("options"), "element": "realization"}, "options"),
        Output({"id": get_uuid("options"), "element": "realization"}, "value"),
        Input({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
        State({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        State({"id": get_uuid("options"), "element": "statistical_option"}, "value"),
        State({"id": get_uuid("options"), "element": "realization"}, "value"),
    )
    def _update_ensemble_options(
        ensemble: str, tree_mode_state: str, stat_option_state: str, real_state: int
    ) -> Tuple[List[Dict[str, Any]], str, str, List[Dict[str, Any]], Optional[int]]:
        """Updates the selection options when the ensemble value changes"""
        tree_mode_options: List[Dict[str, Any]] = [
            {
                "label": "Statistics",
                "value": "statistics",
            },
            {
                "label": "Single realization",
                "value": "single_real",
            },
        ]
        tree_mode_value = (
            tree_mode_state if tree_mode_state is not None else "statistics"
        )
        stat_option_value = (
            stat_option_state if stat_option_state is not None else "mean"
        )

        if not grouptreedata.tree_is_equivalent_in_all_real(ensemble):
            tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
            tree_mode_options[0]["disabled"] = True
            tree_mode_value = "single_real"

        unique_real = grouptreedata.get_ensemble_unique_real(ensemble)

        return (
            tree_mode_options,
            tree_mode_value,
            stat_option_value,
            [{"label": real, "value": real} for real in unique_real],
            real_state if real_state in unique_real else min(unique_real),
        )

    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Input({"id": get_uuid("controls"), "element": "tree_mode"}, "value"),
        Input({"id": get_uuid("options"), "element": "statistical_option"}, "value"),
        Input({"id": get_uuid("options"), "element": "realization"}, "value"),
        Input({"id": get_uuid("filters"), "element": "prod_inj_other"}, "value"),
        State({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _render_grouptree(
        tree_mode: str, stat_option: str, real: int, prod_inj_other: list, ensemble: str
    ) -> list:
        """This callback updates the input dataset to the Grouptree component."""
        data, edge_options, node_options = grouptreedata.create_grouptree_dataset(
            ensemble, tree_mode, stat_option, real, prod_inj_other
        )

        return [
            webviz_subsurface_components.GroupTree(
                id="grouptree",
                data=data,
                edge_options=edge_options,
                node_options=node_options,
            ),
        ]

    @app.callback(
        Output(
            {"id": get_uuid("options"), "element": "statistical_options"},
            "style",
        ),
        Output(
            {"id": get_uuid("options"), "element": "single_real_options"},
            "style",
        ),
        Input(
            {"id": get_uuid("controls"), "element": "tree_mode"},
            "value",
        ),
    )
    def _show_hide_single_real_options(
        tree_mode: str,
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        if tree_mode == "statistics":
            return {"display": "block"}, {"display": "none"}
        return {"display": "none"}, {"display": "block"}
