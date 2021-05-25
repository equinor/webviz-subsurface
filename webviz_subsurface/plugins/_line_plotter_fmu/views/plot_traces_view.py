from typing import Callable, Union, List, Dict
from pathlib import Path

import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def line_traces_view(
    get_uuid: Callable,
) -> html.Div:

    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Plot lines"),
            dcc.Checklist(
                id=get_uuid("traces"),
                options=[
                    {"label": val, "value": val}
                    for val in ["Realizations", "Mean", "P10/P90", "Low/High"]
                ],
                value=["Realizations"],
                labelStyle={"display": "block"},
                persistence=True,
                persistence_type="session",
            ),
            dcc.Checklist(
                id=get_uuid("observations"),
                options=[{"label": val, "value": val} for val in ["Observations"]],
                value=["Observations"],
                labelStyle={"display": "block"},
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def highlight_realizations_view(
    get_uuid: Callable, realizations: List[int]
) -> html.Div:

    return html.Div(
        className="framed",
        style={"fontSize": "0.8em"},
        children=[
            html.H5("Highlight realizations"),
            wcc.Select(
                id=get_uuid("highlight-realizations"),
                options=[{"label": val, "value": val} for val in realizations],
                value=None,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )
