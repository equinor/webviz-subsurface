from typing import Callable, Union, List, Dict
from pathlib import Path

import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface._models import EnsembleTableModelSet


def group_by_view(
    get_uuid: Callable,
    ensemble_names=List[str],
    data_column_names=List[str],
    parameter_names=List[str],
) -> html.Div:
    group_options = ["ENSEMBLE"]
    for col in ["SENSCASE", "SENSTYPE", "SENSNAME"]:
        if col in parameter_names:
            group_options.add(col)
    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Group/aggregate by"),
            dcc.Dropdown(
                id=get_uuid("aggregate"),
                options=[
                    {"value": "mean", "label": "Mean"},
                ],
                placeholder="No aggregation",
                value=None,
            ),
            html.Label("Group on"),
            dcc.Dropdown(
                id=get_uuid("group_level1"),
                options=[{"value": col, "label": col} for col in group_options],
                placeholder="Add group",
                value=None,
                multi=True,
            ),
            html.Div(id=get_uuid("group_wrapper")),
        ],
    )
