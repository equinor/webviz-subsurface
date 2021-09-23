from typing import Callable

from dash import html
import webviz_core_components as wcc


def selections_layout(get_uuid: Callable, ensembles: list) -> wcc.Selectors:
    """Layout for the component input options"""
    controls_uuid = get_uuid("controls")
    return wcc.Selectors(
        id=get_uuid("selections_layout"),
        label="Controls",
        children=[
            wcc.Dropdown(
                label="Ensemble",
                id={"id": controls_uuid, "element": "ensemble"},
                options=[{"label": ens, "value": ens} for ens in ensembles],
                clearable=False,
                value=ensembles[0],
            ),
            wcc.RadioItems(
                label="Mean or realization",
                id={"id": controls_uuid, "element": "tree_mode"},
            ),
            html.Div(
                id={"id": controls_uuid, "element": "single_real_options"},
                children=[
                    wcc.Dropdown(
                        id={"id": controls_uuid, "element": "realization"},
                        options=[],
                        value=None,
                        multi=False,
                    )
                ],
            ),
        ],
    )
