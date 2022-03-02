from typing import List

import webviz_core_components as wcc
from dash import html


def realization_layout(
    uuid: str, realizations: List[int], value: List[int]
) -> html.Div:
    """Layout for the realization filter dialog"""
    return html.Div(
        style={"marginTop": "10px"},
        children=html.Label(
            children=[
                wcc.Select(
                    id={"id": uuid, "element": "realizations"},
                    options=[{"label": real, "value": real} for real in realizations],
                    value=[str(val) for val in value],
                    multi=True,
                    size=20,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )
