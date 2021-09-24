from typing import Callable
from dash import html
import webviz_core_components as wcc

from .selections_view import selections_layout
from .filters_view import filters_layout


def main_view(get_uuid: Callable, ensembles: list) -> wcc.FlexBox:
    """Main layout"""
    return wcc.FlexBox(
        id=get_uuid("layout"),
        children=[
            wcc.FlexColumn(
                flex=1,
                children=[
                    wcc.Frame(
                        style={"height": "82vh"},
                        children=[
                            selections_layout(get_uuid, ensembles),
                            filters_layout(get_uuid),
                        ],
                    )
                ],
            ),
            wcc.FlexColumn(
                flex=5,
                children=[
                    wcc.Frame(
                        style={"height": "82vh"},
                        highlight=False,
                        color="white",
                        children=html.Div(
                            id=get_uuid("grouptree_wrapper"),
                        ),
                    )
                ],
            ),
        ],
    )
