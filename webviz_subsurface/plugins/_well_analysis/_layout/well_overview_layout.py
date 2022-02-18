from typing import Callable, Dict, List

import webviz_core_components as wcc
from dash import html

from .._ensemble_data import EnsembleData


# pylint: disable = too-few-public-methods
class WellOverviewLayoutElements:
    GRAPH = "well-overview-graph"
    ENSEMBLES = "well-overview-ensembles"


def well_overview_tab(
    get_uuid: Callable, data_models: Dict[str, EnsembleData]
) -> wcc.FlexBox:
    """Well overview tab"""
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "87vh"},
                children=controls(get_uuid, data_models),
            ),
            wcc.Frame(
                style={"flex": 4, "height": "87vh"},
                color="white",
                highlight=False,
                id=get_uuid(WellOverviewLayoutElements.GRAPH),
                children=[],
            ),
        ]
    )


def controls(get_uuid: Callable, data_models: Dict[str, EnsembleData]) -> wcc.Frame:
    ensembles = list(data_models.keys())
    return wcc.Selectors(
        label="Selectors",
        children=[
            wcc.Dropdown(
                label="Ensembles",
                id=get_uuid(WellOverviewLayoutElements.ENSEMBLES),
                options=[{"label": col, "value": col} for col in ensembles],
                value=ensembles,
                multi=True,
            ),
        ],
    )
