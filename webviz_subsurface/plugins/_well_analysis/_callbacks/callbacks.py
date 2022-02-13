from typing import Any, Callable, Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate

from .._layout import WellControlLayoutElements, WellOverviewLayoutElements
from .._ensemble_data import EnsembleData


def plugin_callbacks(
    app: Dash, get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> None:
    print("do nothing")
    # @app.callback(
    #     Output(get_uuid(LayoutElements.FORMATIONS_WELL), "value"),
    #     Input(get_uuid(LayoutElements.MAP_GRAPH), "clickData"),
    # )
    # def _dummy_callback()) -> str:
    #     return ""
