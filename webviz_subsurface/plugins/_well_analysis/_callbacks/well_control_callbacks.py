from typing import Callable, Optional, Any, Tuple, List, Dict

import pandas as pd
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from webviz_config import WebvizConfigTheme

from .._layout import WellControlLayoutElements
from .._ensemble_data import EnsembleData
# from ..figures import create_figure
# from ..utils.utils import get_node_info


def well_control_callbacks(
    app: Dash, get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> None:
    print("do nothing")


# def controllers(
#     app: dash.Dash,
#     get_uuid: Callable,
#     smry: pd.DataFrame,
#     gruptree: pd.DataFrame,
#     theme: WebvizConfigTheme,
# ) -> None:
#     @app.callback(
#         Output({"id": get_uuid("plot_controls"), "element": "node"}, "options"),
#         Output({"id": get_uuid("plot_controls"), "element": "node"}, "value"),
#         Output(
#             {"id": get_uuid("pressure_plot_options"), "element": "realization"},
#             "options",
#         ),
#         Output(
#             {"id": get_uuid("pressure_plot_options"), "element": "realization"}, "value"
#         ),
#         Input({"id": get_uuid("plot_controls"), "element": "ensemble"}, "value"),
#         Input({"id": get_uuid("plot_controls"), "element": "node_type"}, "value"),
#     )
#     def _update_dropdowns(
#         ensemble: str, node_type: str
#     ) -> Tuple[
#         List[Dict[str, str]], Optional[str], List[Dict[str, Any]], Optional[int]
#     ]:
#         print("update node dropdown")
#         smry_ens = smry[smry.ENSEMBLE == ensemble].copy()
#         smry_ens.dropna(how="all", axis=1, inplace=True)

#         node_options = get_node_dropdown_options(
#             node_type, smry_ens, list(gruptree.CHILD.unique())
#         )
#         realizations = [
#             {"label": real, "value": real} for real in sorted(smry_ens.REAL.unique())
#         ]
#         return node_options, node_options[0]["value"], realizations, 0

#     # pylint: disable=too-many-locals
#     @app.callback(
#         Output(get_uuid("graph"), "figure"),
#         Input({"id": get_uuid("plot_controls"), "element": ALL}, "value"),
#         Input({"id": get_uuid("settings"), "element": ALL}, "value"),
#         Input({"id": get_uuid("pressure_plot_options"), "element": ALL}, "value"),
#         State({"id": get_uuid("plot_controls"), "element": ALL}, "id"),
#         State({"id": get_uuid("settings"), "element": ALL}, "id"),
#         State({"id": get_uuid("pressure_plot_options"), "element": ALL}, "id"),
#     )
#     def _update_figure(
#         plot_ctrl_vals: list,
#         settings_vals: list,
#         pr_plot_opts_vals: list,
#         plot_ctrl_ids: list,
#         settings_ids: list,
#         pr_plot_opts_ids: list,
#     ) -> go.Figure:
#         print("make chart")
#         plot_ctrl = {
#             id["element"]: value for id, value in zip(plot_ctrl_ids, plot_ctrl_vals)
#         }
#         settings = {
#             id["element"]: value for id, value in zip(settings_ids, settings_vals)
#         }
#         pr_plot_opts = {
#             id["element"]: value
#             for id, value in zip(pr_plot_opts_ids, pr_plot_opts_vals)
#         }

#         ensemble, node_type, node = (
#             plot_ctrl["ensemble"],
#             plot_ctrl["node_type"],
#             plot_ctrl["node"],
#         )
#         if ensemble is None or node_type is None or node is None:
#             fig = go.Figure()
#             fig.update_layout(plot_bgcolor="white", title="No data")
#             return fig

#         smry_ens = smry[smry.ENSEMBLE == ensemble]
#         gruptree_ens = gruptree[gruptree.ENSEMBLE == ensemble]
#         node_info = get_node_info(gruptree_ens, node_type, node, smry_ens.DATE.min())
#         return create_figure(node_info, smry_ens, settings, pr_plot_opts, theme)

#     @app.callback(
#         Output(
#             {"id": get_uuid("pressure_plot_options"), "element": "single_real_options"},
#             component_property="style",
#         ),
#         Input(
#             {"id": get_uuid("pressure_plot_options"), "element": "mean_or_single_real"},
#             "value",
#         ),
#     )
#     def _show_hide_single_real_options(mean_or_single_real: str) -> Dict:
#         if mean_or_single_real == "plot_mean":
#             return {"display": "none"}
#         return {"display": "block"}


# def get_node_dropdown_options(
#     node_type: str, smry: pd.DataFrame, tree_nodes: list
# ) -> List[Dict[str, str]]:
#     """Description"""

#     if node_type == "well":
#         nodes = [vec.split(":")[1] for vec in smry.columns if vec.startswith("WMCTL")]
#     elif node_type == "field_group":
#         nodes = [
#             vec.split(":")[1]
#             for vec in smry.columns
#             if vec.startswith("GMCTP") and vec.split(":")[1] in tree_nodes
#         ] + ["FIELD"]
#     else:
#         raise ValueError(f"Node type {node_type} not implemented.")
#     if not nodes:
#         return []
#     return [{"label": node, "value": node} for node in nodes]
