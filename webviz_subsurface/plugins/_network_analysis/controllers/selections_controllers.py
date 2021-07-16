from typing import Callable, Optional, Any

import pandas as pd
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

import webviz_core_components as wcc

from ..figures import make_node_pressure_graph, make_area_graph


# pylint: disable=too-many-statements, too-many-locals, too-many-arguments
def selections_controllers(
    app: dash.Dash, get_uuid: Callable, smry: pd.DataFrame
) -> None:
    @app.callback(
        Output(get_uuid("node_dropdown"), "options"),
        Output(get_uuid("node_dropdown"), "value"),
        Input(get_uuid("ensemble_dropdown"), "value"),
        Input(get_uuid("node_type_radioitems"), "value"),
    )
    def _update_node_dropdown(ensemble: str, node_type: str) -> list:
        print("update node dropdown")
        smry_ens = smry[smry.ENSEMBLE == ensemble].copy()
        smry_ens.dropna(how="all", axis=1, inplace=True)

        if node_type == "well":
            nodes = [
                vec.split(":")[1] for vec in smry_ens.columns if vec.startswith("WMCTL")
            ]
        elif node_type == "field_group":
            nodes = [
                vec.split(":")[1] for vec in smry_ens.columns if vec.startswith("GMCTP")
            ] + ["FIELD"]
        else:
            raise ValueError(f"Node type {node_type} not implemented.")
        if not nodes:
            return [], None
        return [{"label": node, "value": node} for node in nodes], nodes[0]

    @app.callback(
        Output(get_uuid("ctrl_mode_graph"), "figure"),
        Output(get_uuid("pressures_graph"), "figure"),
        Input(get_uuid("ensemble_dropdown"), "value"),
        Input(get_uuid("node_type_radioitems"), "value"),
        Input(get_uuid("node_dropdown"), "value"),
    )
    def _update_graph(ensemble: str, node_type: str, node: str):
        print("make chart")

        if ensemble is None or node_type is None or node is None:
            # Format this a bit more
            fig = go.Figure()
            fig.update_layout(plot_bgcolor="white", title="No data")
            return fig, fig

        smry_ens = smry[smry.ENSEMBLE == ensemble]

        return (
            make_area_graph(node_type, node, smry_ens),
            make_node_pressure_graph(node_type, node, smry_ens),
        )