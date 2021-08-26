from typing import Callable

import dash_html_components as html
import webviz_core_components as wcc


def selections_layout(get_uuid: Callable, ensembles: list) -> wcc.Frame:
    return wcc.Frame(
        id=get_uuid("selections_layout"),
        style={"height": "82vh"},
        children=[
            wcc.Selectors(
                label="Ensemble",
                children=[
                    wcc.Dropdown(
                        id=get_uuid("ensemble_dropdown"),
                        options=[{"label": ens, "value": ens} for ens in ensembles],
                        clearable=False,
                        value=ensembles[0],
                    ),
                ],
            ),
        ],
    )
