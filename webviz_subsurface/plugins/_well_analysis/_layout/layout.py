from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import html

from .._ensemble_data import EnsembleData


# pylint: disable = too-few-public-methods
class LayoutElements:
    WELL_OVERVIEW_GRAPH = "well-overview-graph"


def main_layout(get_uuid: Callable, data_models: Dict[str, EnsembleData]) -> wcc.Tabs:
    """Main layout"""
    tabs = [
        wcc.Tab(label="Well Overview", children=well_overview_tab(get_uuid)),
        wcc.Tab(label="Well Control", children="Not implemented"),
    ]

    return wcc.Tabs(children=tabs)


def well_overview_tab(get_uuid: Callable) -> wcc.FlexBox:
    """Well overview tab"""
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "87vh"},
                children=[],
            ),
            wcc.Frame(
                style={"flex": 4, "height": "87vh"},
                color="white",
                highlight=False,
                id=get_uuid(LayoutElements.WELL_OVERVIEW_GRAPH),
                children=[],
            ),
        ]
    )
