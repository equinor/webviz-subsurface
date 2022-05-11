from typing import Callable, List

import webviz_core_components as wcc
from dash import html

from ._types import NodeType, StatOptions


# pylint: disable = too-few-public-methods
class LayoutElements:
    LAYOUT = "layout"
    OPTIONS_LAYOUT = "options-layout"
    FILTERS_LAYOUT = "filters-layout"
    SELECTIONS_LAYOUT = "selections-layout"
    GRAPH = "graph"
    NODETYPE_FILTER = "node-type-filter"
    STATISTICAL_OPTIONS = "statistical-options"
    STATISTICAL_OPTION = "statistical-option"
    SINGLE_REAL_OPTIONS = "single-real-options"
    REALIZATION = "realization"
    ENSEMBLE = "ensemble"
    TREE_MODE = "tree-mode"


def main_layout(get_uuid: Callable[[str], str], ensembles: List[str]) -> wcc.FlexBox:
    """Main layout"""
    return wcc.FlexBox(
        children=[
            wcc.FlexColumn(
                flex=1,
                children=[
                    wcc.Frame(
                        style={"height": "82vh"},
                        children=[
                            selections_layout(get_uuid, ensembles),
                            options_layout(get_uuid),
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
                            id=get_uuid(LayoutElements.GRAPH),
                        ),
                    )
                ],
            ),
        ],
    )


def filters_layout(get_uuid: Callable[[str], str]) -> wcc.Selectors:
    """The filters part of the menu"""
    return wcc.Selectors(
        id=get_uuid(LayoutElements.FILTERS_LAYOUT),
        label="Filters",
        children=[
            wcc.SelectWithLabel(
                label="Prod/Inj/Other",
                id=get_uuid(LayoutElements.NODETYPE_FILTER),
                options=[
                    {"label": "Production", "value": NodeType.PROD.value},
                    {"label": "Injection", "value": NodeType.INJ.value},
                    {"label": "Other", "value": NodeType.OTHER.value},
                ],
                value=[NodeType.PROD.value, NodeType.INJ.value, NodeType.OTHER.value],
                multi=True,
                size=3,
            )
        ],
    )


def options_layout(get_uuid: Callable[[str], str]) -> wcc.Selectors:
    """The options part of the menu"""
    return wcc.Selectors(
        id=get_uuid(LayoutElements.OPTIONS_LAYOUT),
        label="Options",
        children=[
            html.Div(
                id=get_uuid(LayoutElements.STATISTICAL_OPTIONS),
                children=[
                    wcc.RadioItems(
                        id=get_uuid(LayoutElements.STATISTICAL_OPTION),
                        options=[
                            {"label": "Mean", "value": StatOptions.MEAN.value},
                            {"label": "P10 (high)", "value": StatOptions.P10.value},
                            {"label": "P50 (median)", "value": StatOptions.P50.value},
                            {"label": "P90 (low)", "value": StatOptions.P90.value},
                            {"label": "Maximum", "value": StatOptions.MAX.value},
                            {"label": "Minimum", "value": StatOptions.MIN.value},
                        ],
                    )
                ],
            ),
            html.Div(
                id=get_uuid(LayoutElements.SINGLE_REAL_OPTIONS),
                children=[
                    wcc.Dropdown(
                        label="Realization",
                        id=get_uuid(LayoutElements.REALIZATION),
                        options=[],
                        value=None,
                        multi=False,
                    )
                ],
            ),
        ],
    )


def selections_layout(
    get_uuid: Callable[[str], str], ensembles: List[str]
) -> wcc.Selectors:
    """Layout for the component input options"""
    return wcc.Selectors(
        id=get_uuid(LayoutElements.SELECTIONS_LAYOUT),
        label="Controls",
        children=[
            wcc.Dropdown(
                label="Ensemble",
                id=get_uuid(LayoutElements.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                clearable=False,
                value=ensembles[0],
            ),
            wcc.RadioItems(
                label="Statistics or realization", id=get_uuid(LayoutElements.TREE_MODE)
            ),
        ],
    )
