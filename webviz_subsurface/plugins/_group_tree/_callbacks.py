from typing import Any, Callable, Dict, List, Optional, Tuple

import dash
import webviz_subsurface_components
from dash.dependencies import Input, Output, State

from ._ensemble_group_tree_data import EnsembleGroupTreeData
from ._layout import LayoutElements
from ._types import NodeType, StatOptions, TreeModeOptions


def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable[[str], str],
    group_tree_data: Dict[str, EnsembleGroupTreeData],
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.TREE_MODE), "options"),
        Output(get_uuid(LayoutElements.TREE_MODE), "value"),
        Output(get_uuid(LayoutElements.STATISTICAL_OPTION), "value"),
        Output(get_uuid(LayoutElements.REALIZATION), "options"),
        Output(get_uuid(LayoutElements.REALIZATION), "value"),
        Input(get_uuid(LayoutElements.ENSEMBLE), "value"),
        State(get_uuid(LayoutElements.TREE_MODE), "value"),
        State(get_uuid(LayoutElements.STATISTICAL_OPTION), "value"),
        State(get_uuid(LayoutElements.REALIZATION), "value"),
    )
    def _update_ensemble_options(
        ensemble_name: str,
        tree_mode_state: str,
        stat_option_state: str,
        real_state: int,
    ) -> Tuple[List[Dict[str, Any]], str, str, List[Dict[str, Any]], Optional[int]]:
        """Updates the selection options when the ensemble value changes"""
        tree_mode_options: List[Dict[str, Any]] = [
            {
                "label": "Statistics",
                "value": TreeModeOptions.STATISTICS.value,
            },
            {
                "label": "Single realization",
                "value": TreeModeOptions.SINGLE_REAL.value,
            },
        ]
        tree_mode = (
            TreeModeOptions(tree_mode_state)
            if tree_mode_state is not None
            else TreeModeOptions.STATISTICS
        )
        stat_option = (
            StatOptions(stat_option_state)
            if stat_option_state is not None
            else StatOptions.MEAN
        )

        ensemble = group_tree_data[ensemble_name]
        if not ensemble.tree_is_equivalent_in_all_real():
            tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
            tree_mode_options[0]["disabled"] = True
            tree_mode = TreeModeOptions.SINGLE_REAL

        unique_real = ensemble.get_unique_real()

        return (
            tree_mode_options,
            tree_mode.value,
            stat_option.value,
            [{"label": real, "value": real} for real in unique_real],
            real_state if real_state in unique_real else min(unique_real),
        )

    @app.callback(
        Output(get_uuid(LayoutElements.GRAPH), "children"),
        Input(get_uuid(LayoutElements.TREE_MODE), "value"),
        Input(get_uuid(LayoutElements.STATISTICAL_OPTION), "value"),
        Input(get_uuid(LayoutElements.REALIZATION), "value"),
        Input(get_uuid(LayoutElements.NODETYPE_FILTER), "value"),
        State(get_uuid(LayoutElements.ENSEMBLE), "value"),
    )
    def _render_grouptree(
        tree_mode: str,
        stat_option: str,
        real: int,
        node_types: list,
        ensemble_name: str,
    ) -> list:
        """This callback updates the input dataset to the Grouptree component."""
        data, edge_options, node_options = group_tree_data[
            ensemble_name
        ].create_grouptree_dataset(
            TreeModeOptions(tree_mode),
            StatOptions(stat_option),
            real,
            [NodeType(tpe) for tpe in node_types],
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
        Output(get_uuid(LayoutElements.STATISTICAL_OPTIONS), "style"),
        Output(get_uuid(LayoutElements.SINGLE_REAL_OPTIONS), "style"),
        Input(get_uuid(LayoutElements.TREE_MODE), "value"),
    )
    def _show_hide_single_real_options(
        tree_mode: str,
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        if TreeModeOptions(tree_mode) is TreeModeOptions.STATISTICS:
            return {"display": "block"}, {"display": "none"}
        return {"display": "none"}, {"display": "block"}
