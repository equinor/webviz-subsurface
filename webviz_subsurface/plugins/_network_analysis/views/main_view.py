from typing import Callable

import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme

from .selections_view import selections_layout


def main_view(get_uuid: Callable, ensembles: list) -> wcc.FlexBox:
    return wcc.FlexBox(
        id=get_uuid("layout"),
        children=[
            wcc.FlexColumn(flex=1, children=selections_layout(get_uuid, ensembles)),
            wcc.FlexColumn(
                flex=4,
                children=[
                    wcc.Frame(
                        style={"height": "82vh"},
                        highlight=False,
                        color="white",
                        children=wcc.Graph(
                            style={"height": "82vh"},
                            id=get_uuid("graph"),
                        ),
                    ),
                    # wcc.Frame(
                    #     style={"height": "40vh"},
                    #     highlight=False,
                    #     color="white",
                    #     children=wcc.Graph(
                    #         style={"height": "40vh"},
                    #         id=get_uuid("pressures_graph"),
                    #     ),
                    # ),
                ],
            ),
        ],
    )
