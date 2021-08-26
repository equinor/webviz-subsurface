from typing import Callable, Optional, Any, Tuple, List, Dict
import json
import pandas as pd
import dash
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objects as go
from webviz_config import WebvizConfigTheme
import webviz_subsurface_components

from ..utils.utils import create_ensemble_dataset


def controllers(
    app: dash.Dash,
    get_uuid: Callable,
    ens_paths,
    gruptree_file,
    time_index,
) -> None:
    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Output(get_uuid("grouptree_wrapper"), "style"),
        Input(get_uuid("ensemble_dropdown"), "value"),
    )
    def _render_grouptree(ensemble_name: str) -> list:

        data = json.load(
            create_ensemble_dataset(
                ensemble_name,
                ens_paths[ensemble_name],
                gruptree_file,
                time_index,
            )
        )
        return [
            webviz_subsurface_components.GroupTree(id="grouptree", data=data),
            {"padding": "10px"},
        ]
