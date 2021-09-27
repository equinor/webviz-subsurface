from typing import Callable, List

import webviz_core_components as wcc
from dash import html


def line_traces_view(
    get_uuid: Callable,
) -> html.Div:

    return wcc.Selectors(
        label="Plot data",
        children=[
            wcc.RadioItems(
                id=get_uuid("mode"),
                options=[
                    {"value": "lines", "label": "Lines"},
                    {"value": "markers", "label": "Points"},
                ],
                value="lines",
            ),
            wcc.Checklist(
                id=get_uuid("traces"),
                options=[
                    {"label": val, "value": val}
                    for val in ["Realizations", "Mean", "P10/P90", "Low/High"]
                ],
                value=["Realizations"],
                labelStyle={"display": "block"},
            ),
            wcc.Checklist(
                id=get_uuid("observations"),
                options=[{"label": val, "value": val} for val in ["Observations"]],
                value=["Observations"],
                labelStyle={"display": "block"},
            ),
            wcc.Label(id=get_uuid("statistics_warning"), children=""),
        ],
    )


def highlight_realizations_view(
    get_uuid: Callable, realizations: List[int]
) -> html.Div:

    return wcc.Selectors(
        label="Highlight realizations",
        children=[
            wcc.Select(
                id=get_uuid("highlight-realizations"),
                options=[{"label": val, "value": val} for val in realizations],
                value=None,
            ),
            html.Button(
                id=get_uuid("clear-highlight-realizations"),
                children="Clear",
            ),
        ],
    )
