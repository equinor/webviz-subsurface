from typing import Callable

import webviz_core_components as wcc
from dash import dcc, html


# pylint: disable = too-few-public-methods
class LayoutElements:
    LAYOUT = "layout"
    ENSEMBLE_DROPDOWN = "ensemble_dropdown"
    WELL_COMPLETIONS_COMPONENT = "well_completions_component"


def main_layout(get_uuid: Callable, ensembles: list) -> html.Div:
    return html.Div(
        id=get_uuid(LayoutElements.LAYOUT),
        children=[
            dcc.Store(
                id=get_uuid(LayoutElements.ENSEMBLE_DROPDOWN), storage_type="session"
            ),
            wcc.FlexBox(
                children=[
                    wcc.Selectors(
                        label="Ensemble",
                        children=[
                            wcc.Dropdown(
                                id=get_uuid(LayoutElements.ENSEMBLE_DROPDOWN),
                                options=[
                                    {"label": ens, "value": ens} for ens in ensembles
                                ],
                                clearable=False,
                                value=ensembles[0],
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                    html.Div(style={"flex": 4}),
                ],
            ),
            html.Div(
                id=get_uuid(LayoutElements.WELL_COMPLETIONS_COMPONENT),
            ),
        ],
    )


def layout_tour_steps(get_uuid: Callable) -> list:
    return [
        {
            "id": get_uuid(LayoutElements.LAYOUT),
            "content": "Dashboard vizualizing Eclipse well completion output.",
        },
        {
            "id": get_uuid(LayoutElements.ENSEMBLE_DROPDOWN),
            "content": "Select ensemble.",
        },
        {
            "id": get_uuid(LayoutElements.WELL_COMPLETIONS_COMPONENT),
            "content": (
                "Visualization of the well completions. "
                "Time slider for selecting which time steps to display. "
                "Different vizualisation and filtering alternatives are available "
                "in the upper right corner."
            ),
        },
    ]
