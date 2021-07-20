from typing import Callable, Optional, Any, Tuple, List

import pandas as pd
import dash
from dash.dependencies import Input, Output, ALL
import plotly.graph_objects as go

from ..figures import make_node_pressure_graph, make_area_graph
from ..utils.utils import get_upstream_nodes, get_node_field


def controllers(
    app: dash.Dash, get_uuid: Callable, smry: pd.DataFrame, gruptree: pd.DataFrame
) -> None:
    @app.callback(
        Output({"id": get_uuid("plot_controls"), "element": "node"}, "options"),
        Output({"id": get_uuid("plot_controls"), "element": "node"}, "value"),
        Output(
            {"id": get_uuid("pressure_plot_options"), "element": "realization"},
            "options",
        ),
        Output(
            {"id": get_uuid("pressure_plot_options"), "element": "realization"}, "value"
        ),
        Input({"id": get_uuid("plot_controls"), "element": "ensemble"}, "value"),
        Input({"id": get_uuid("plot_controls"), "element": "node_type"}, "value"),
    )
    def _update_dropdowns(
        ensemble: str, node_type: str
    ) -> Tuple[List[Any], Optional[str]]:
        print("update node dropdown")
        smry_ens = smry[smry.ENSEMBLE == ensemble].copy()
        smry_ens.dropna(how="all", axis=1, inplace=True)

        node_options = get_node_dropdown_options(node_type, smry_ens)
        realizations = [
            {"label": real, "value": real} for real in sorted(smry_ens.REAL.unique())
        ]
        return node_options, node_options[0]["value"], realizations, 0

    @app.callback(
        Output(get_uuid("ctrl_mode_graph"), "figure"),
        Output(get_uuid("pressures_graph"), "figure"),
        Input({"id": get_uuid("plot_controls"), "element": ALL}, "id"),
        Input({"id": get_uuid("plot_controls"), "element": ALL}, "value"),
        Input({"id": get_uuid("pressure_plot_options"), "element": ALL}, "id"),
        Input({"id": get_uuid("pressure_plot_options"), "element": ALL}, "value"),
    )
    def _update_graphs(
        plot_ctrl_ids: list,
        plot_ctrl_vals: list,
        pr_plot_opts_ids: list,
        pr_plot_opts_vals: list,
    ) -> Tuple[go.Figure, go.Figure]:
        print("make chart")
        plot_ctrl = {
            id["element"]: value for id, value in zip(plot_ctrl_ids, plot_ctrl_vals)
        }
        pr_plot_opts = {
            id["element"]: value
            for id, value in zip(pr_plot_opts_ids, pr_plot_opts_vals)
        }

        ensemble, node_type, node = (
            plot_ctrl["ensemble"],
            plot_ctrl["node_type"],
            plot_ctrl["node"],
        )
        if ensemble is None or node_type is None or node is None:
            fig = go.Figure()
            fig.update_layout(plot_bgcolor="white", title="No data")
            return fig, fig

        smry_ens = smry[smry.ENSEMBLE == ensemble]
        if gruptree.empty or ensemble not in gruptree.ENSEMBLE.unique():
            upstream_nodes = [
                {
                    "start_date": smry_ens.DATE.min(),
                    "end_date": smry_ens.DATE.max(),
                    "nodes": [get_node_field(node_type, node)],
                }
            ]
        else:
            upstream_nodes = get_upstream_nodes(
                gruptree[gruptree.ENSEMBLE == ensemble], node_type, node
            )

        return (
            make_area_graph(node_type, node, smry_ens),
            make_node_pressure_graph(upstream_nodes, smry_ens, pr_plot_opts),
        )

    @app.callback(
        Output(
            {
                "id": get_uuid("pressure_plot_options"),
                "element": "realization",
            },
            "disabled",
        ),
        Input(
            {"id": get_uuid("pressure_plot_options"), "element": "mean_or_single_real"},
            "value",
        ),
    )
    def _show_hide_realizations_dropdown(mean_or_single_real: str) -> bool:
        return True if mean_or_single_real == "plot_mean" else False


def get_node_dropdown_options(node_type: str, smry: pd.DataFrame) -> list:
    """Description"""

    if node_type == "well":
        nodes = [vec.split(":")[1] for vec in smry.columns if vec.startswith("WMCTL")]
    elif node_type == "field_group":
        nodes = [
            vec.split(":")[1] for vec in smry.columns if vec.startswith("GMCTP")
        ] + ["FIELD"]
    else:
        raise ValueError(f"Node type {node_type} not implemented.")
    if not nodes:
        return []
    return [{"label": node, "value": node} for node in nodes]
