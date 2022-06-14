from typing import Any, Callable, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Dash, Input, Output, State
from webviz_config import WebvizConfigTheme

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import create_well_control_figure
from .._layout import WellControlLayoutElements
from .._types import PressurePlotMode


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
        State(get_uuid(WellControlLayoutElements.WELL), "value"),
        State(get_uuid(WellControlLayoutElements.REAL), "value"),
    )
    def _update_dropdowns(
        ensemble: str, state_well: str, state_real: int
    ) -> Tuple[
        List[Dict[str, str]], Optional[str], List[Dict[str, Any]], Optional[int]
    ]:
        """Updates the well and realization dropdowns with ensemble values"""
        wells = data_models[ensemble].wells
        reals = data_models[ensemble].realizations
        return (
            [{"label": well, "value": well} for well in wells],
            state_well if state_well in wells else wells[0],
            [{"label": real, "value": real} for real in reals],
            state_real if state_real in reals else reals[0],
        )

    @app.callback(
        Output(get_uuid(WellControlLayoutElements.GRAPH), "children"),
        Input(get_uuid(WellControlLayoutElements.WELL), "value"),
        Input(get_uuid(WellControlLayoutElements.INCLUDE_BHP), "value"),
        Input(get_uuid(WellControlLayoutElements.PRESSURE_PLOT_MODE), "value"),
        Input(get_uuid(WellControlLayoutElements.REAL), "value"),
        Input(get_uuid(WellControlLayoutElements.CTRLMODE_BAR), "value"),
        Input(get_uuid(WellControlLayoutElements.SHARED_XAXES), "value"),
        State(get_uuid(WellControlLayoutElements.ENSEMBLE), "value"),
        prevent_initial_call=True,
    )
    def _update_figure(
        well: str,
        include_bhp: List[str],
        pressure_plot_mode_string: str,
        real: int,
        display_ctrlmode_bar: bool,
        shared_xaxes: List[str],
        ensemble: str,
    ) -> List[Optional[Any]]:
        """Updates the well control figure"""
        pressure_plot_mode = PressurePlotMode(pressure_plot_mode_string)
        fig = create_well_control_figure(
            data_models[ensemble].get_node_info(well, pressure_plot_mode, real),
            data_models[ensemble].summary_data,
            pressure_plot_mode,
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
        Input(get_uuid(WellControlLayoutElements.PRESSURE_PLOT_MODE), "value"),
    )
    def _show_hide_single_real_options(pressure_plot_mode: str) -> Dict[str, str]:
        """Hides or unhides the realization dropdown according to whether mean
        or single realization is selected.
        """
        if PressurePlotMode(pressure_plot_mode) == PressurePlotMode.MEAN:
            return {"display": "none"}
        return {"display": "block"}
