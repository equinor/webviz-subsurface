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
                            {"label": "P10 (high)", "value": "p10"},
                            {"label": "P50 (median)", "value": "p50"},
                            {"label": "P90 (low)", "value": "p90"},
                            {"label": "Maximum", "value": "max"},
                            {"label": "Minimum", "value": "min"},
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
