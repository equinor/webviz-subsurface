from typing import Callable

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc

from webviz_subsurface._models import EnsembleTableModelSet


def main_view(get_uuid: Callable, tablemodel: EnsembleTableModelSet) -> html.Div:
    return wcc.FlexBox(
        children=[
            html.Div(
                style={"flex": 1},
                children=[sidebar_view(get_uuid=get_uuid, tablemodel=tablemodel)],
            ),
            html.Div(style={"flex": 5}, children=[plot_view(get_uuid=get_uuid)]),
        ]
    )


def sidebar_view(get_uuid: Callable, tablemodel: EnsembleTableModelSet) -> wcc.FlexBox:
    return html.Div([selectors(get_uuid=get_uuid, tablemodel=tablemodel)])


def plot_view(get_uuid: Callable) -> html.Div:
    return html.Div(dcc.Graph(id=get_uuid("graph")))


def selectors(get_uuid: Callable, tablemodel: EnsembleTableModelSet) -> html.Div:
    uuid: str = get_uuid("selectors")
    return html.Div(
        children=[
            ensemble_selector(uuid=uuid, tablemodel=tablemodel),
            x_selector(uuid=uuid),
            y_selector(uuid=uuid),
        ]
    )


def ensemble_selector(
    uuid: str, tablemodel: EnsembleTableModelSet, flex: int = 1
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Ensemble"),
            dcc.Dropdown(
                id={"id": uuid, "attribute": "ensemble"},
                options=[
                    {"label": ens, "value": ens} for ens in tablemodel.ensemble_names()
                ],
                value=tablemodel.ensemble_names()[0],
                clearable=False,
            ),
        ],
    )


def x_selector(uuid: str, flex: int = 1) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Data for x-axis"),
            dcc.Dropdown(
                id={"id": uuid, "attribute": "x_selector"},
                clearable=False,
            ),
        ],
    )


def y_selector(uuid: str, flex: int = 1) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label("Data for y-axis"),
            dcc.Dropdown(
                id={"id": uuid, "attribute": "y_selector"},
                clearable=False,
            ),
        ],
    )
