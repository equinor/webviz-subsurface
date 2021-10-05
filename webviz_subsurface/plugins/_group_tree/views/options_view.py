from typing import Callable

import webviz_core_components as wcc
from dash import html


def options_layout(get_uuid: Callable) -> wcc.Selectors:
    """The options part of the menu"""
    options_uuid = get_uuid("options")
    return wcc.Selectors(
        id=get_uuid("options_layout"),
        label="Options",
        children=[
            html.Div(
                id={"id": options_uuid, "element": "statistical_options"},
                children=[
                    wcc.RadioItems(
                        id={"id": options_uuid, "element": "statistical_option"},
                        options=[
                            {"label": "Mean", "value": "mean"},
                            {"label": "P50/Median", "value": "p50"},
                            {"label": "P10", "value": "p10"},
                            {"label": "P90", "value": "p90"},
                            {"label": "Max", "value": "max"},
                            {"label": "Min", "value": "min"},
                        ],
                    )
                ],
            ),
            html.Div(
                id={"id": options_uuid, "element": "single_real_options"},
                children=[
                    wcc.Dropdown(
                        label="Realization",
                        id={"id": options_uuid, "element": "realization"},
                        options=[],
                        value=None,
                        multi=False,
                    )
                ],
            ),
        ],
    )
