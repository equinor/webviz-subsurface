from typing import Callable, Optional, Any, Tuple, List, Dict

import pandas as pd
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from webviz_config import WebvizConfigTheme

from .._layout import WellControlLayoutElements
from .._ensemble_data import EnsembleData
from .._figures import create_well_control_figure

# from ..utils.utils import get_node_info


def well_control_callbacks(
    app: Dash, get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> None:
    @app.callback(
        Output(get_uuid(WellControlLayoutElements.WELL), "options"),
        Output(get_uuid(WellControlLayoutElements.WELL), "value"),
        Output(get_uuid(WellControlLayoutElements.REAL), "options"),
        Output(get_uuid(WellControlLayoutElements.REAL), "value"),
        Input(get_uuid(WellControlLayoutElements.ENSEMBLE), "value"),
    )
    def _update_dropdowns(
        ensemble: str,
    ) -> Tuple[
        List[Dict[str, str]], Optional[str], List[Dict[str, Any]], Optional[int]
    ]:
        print("well control - update dropdowns")
        wells = data_models[ensemble].wells
        reals = data_models[ensemble].realizations
        return (
            [{"label": well, "value": well} for well in wells],
            wells[0],
            [{"label": real, "value": real} for real in reals],
            reals[0],
        )

    @app.callback(
        Output(get_uuid(WellControlLayoutElements.GRAPH), "children"),
        # Input(WellControlLayoutElements.ENSEMBLE, "value"),
        Input(get_uuid(WellControlLayoutElements.WELL), "value"),
        # Input(WellControlLayoutElements.INCLUDE_BHP, "value"),
        # Input(WellControlLayoutElements.MEAN_OR_REAL, "value"),
        # Input(WellControlLayoutElements.REAL, "value"),
        # Input(WellControlLayoutElements.CTRLMODE_BAR, "value"),
        # Input(WellControlLayoutElements.SHARED_XAXIS, "value"),
        prevent_initial_call=True,
    )
    def _update_figure(
        # ensemble: str, well: str, include_bhp: bool, mean_or_single_real: bool, real: int, ctrlmode_bar: bool, shared_xaxis: bool
        well: str,
    ) -> List[Optional[Any]]:
        print("make wellcontrol graph")
        # print(ensemble, well, include_bhp, mean_or_single_real, real, ctrlmode_bar, shared_xaxis)

        # smry_ens = smry[smry.ENSEMBLE == ensemble]
        # gruptree_ens = gruptree[gruptree.ENSEMBLE == ensemble]
        # node_info = get_node_info(gruptree_ens, node_type, node, smry_ens.DATE.min())
        return [
            "Not implemented"
        ]  # create_well_control_figure(node_info, smry_ens, settings, pr_plot_opts, theme)

    @app.callback(
        Output(
            get_uuid(WellControlLayoutElements.SINGLE_REAL_OPTIONS),
            component_property="style",
        ),
        Input(get_uuid(WellControlLayoutElements.MEAN_OR_REAL), "value"),
    )
    def _show_hide_single_real_options(mean_or_single_real: str) -> Dict[str, str]:
        if mean_or_single_real == "plot_mean":
            return {"display": "none"}
        return {"display": "block"}
