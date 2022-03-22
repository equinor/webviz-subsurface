from typing import Any, Callable, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Dash, Input, Output, State
from webviz_config import WebvizConfigTheme

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import create_well_control_figure
from .._layout import WellControlLayoutElements


def well_control_callbacks(
    app: Dash,
    get_uuid: Callable,
    data_models: Dict[str, EnsembleWellAnalysisData],
    theme: WebvizConfigTheme,
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
        """Updates the well and realization dropdowns with ensemble values"""
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
        Input(get_uuid(WellControlLayoutElements.WELL), "value"),
        Input(get_uuid(WellControlLayoutElements.INCLUDE_BHP), "value"),
        Input(get_uuid(WellControlLayoutElements.MEAN_OR_REAL), "value"),
        Input(get_uuid(WellControlLayoutElements.REAL), "value"),
        Input(get_uuid(WellControlLayoutElements.CTRLMODE_BAR), "value"),
        Input(get_uuid(WellControlLayoutElements.SHARED_XAXES), "value"),
        State(get_uuid(WellControlLayoutElements.ENSEMBLE), "value"),
        prevent_initial_call=True,
    )
    def _update_figure(
        well: str,
        include_bhp: List[str],
        mean_or_single_real: str,
        real: int,
        display_ctrlmode_bar: bool,
        shared_xaxes: List[str],
        ensemble: str,
    ) -> List[Optional[Any]]:
        """Updates the well control figure"""
        fig = create_well_control_figure(
            data_models[ensemble].get_node_info(well),
            data_models[ensemble].summary_data,
            mean_or_single_real,
            real,
            display_ctrlmode_bar,
            "shared_xaxes" in shared_xaxes,
            "include_bhp" in include_bhp,
            theme,
        )

        return wcc.Graph(style={"height": "87vh"}, figure=fig)

    @app.callback(
        Output(
            get_uuid(WellControlLayoutElements.SINGLE_REAL_OPTIONS),
            component_property="style",
        ),
        Input(get_uuid(WellControlLayoutElements.MEAN_OR_REAL), "value"),
    )
    def _show_hide_single_real_options(mean_or_single_real: str) -> Dict[str, str]:
        """Hides or unhides the realization dropdown according to whether mean
        or single realization is selected.
        """
        if mean_or_single_real == "plot_mean":
            return {"display": "none"}
        return {"display": "block"}
