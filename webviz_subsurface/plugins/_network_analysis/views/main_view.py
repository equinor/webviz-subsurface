from typing import Callable

import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme


def main_view(
    get_uuid: Callable, theme: WebvizConfigTheme, ensembles: list
) -> wcc.FlexBox:
    return wcc.FlexBox(
        id=get_uuid("layout"),
        children=[
            wcc.FlexColumn(flex=1, children=selectors_layout(get_uuid, ensembles)),
            wcc.FlexColumn(
                flex=4,
                children=[
                    wcc.Frame(
                        style={"height": "45vh"},
                        highlight=False,
                        color="white",
                        children=wcc.Graph(
                            style={"height": "45vh"},
                            id=get_uuid("ctrl_mode_graph"),
                        ),
                    ),
                    wcc.Frame(
                        style={"height": "45vh"},
                        highlight=False,
                        color="white",
                        children=wcc.Graph(
                            style={"height": "45vh"},
                            id=get_uuid("pressures_graph"),
                        ),
                    ),
                ],
            ),
        ],
    )


def selectors_layout(get_uuid: Callable, ensembles: list) -> wcc.Frame:
    return wcc.Frame(
        style={"height": "40vh"},
        children=[
            wcc.Selectors(
                label="Ensemble",
                children=wcc.Dropdown(
                    id=get_uuid("ensemble_dropdown"),
                    options=[{"label": col, "value": col} for col in ensembles],
                    value=ensembles[0],
                    multi=False,
                ),
            ),
            wcc.Selectors(
                label="Node type:",
                children=wcc.RadioItems(
                    id=get_uuid("node_type_radioitems"),
                    options=[
                        {
                            "label": "Well",
                            "value": "well",
                        },
                        {
                            "label": "Field / Group",
                            "value": "field_group",
                        },
                    ],
                    value="well",
                ),
            ),
            wcc.Selectors(
                label="Node",
                children=wcc.Dropdown(
                    id=get_uuid("node_dropdown"),
                    options=[],
                    value=None,
                    multi=False,
                ),
            ),
        ],
    )
