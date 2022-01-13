from typing import Callable

import webviz_core_components as wcc
from dash import html


def main_layout(get_uuid: Callable, ensembles: list) -> wcc.FlexBox:
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
                            id=get_uuid("grouptree_wrapper"),
                        ),
                    )
                ],
            ),
        ],
    )


def filters_layout(get_uuid: Callable) -> wcc.Selectors:
    """The filters part of the menu"""
    filters_uuid = get_uuid("filters")
    return wcc.Selectors(
        id=get_uuid("filters_layout"),
        label="Filters",
        children=[
            wcc.SelectWithLabel(
                label="Prod/Inj/Other",
                id={"id": filters_uuid, "element": "prod_inj_other"},
                options=[
                    {"label": "Production", "value": "prod"},
                    {"label": "Injection", "value": "inj"},
                    {"label": "Other", "value": "other"},
                ],
                value=["prod", "inj", "other"],
                multi=True,
                size=3,
            )
        ],
    )


def options_layout(get_uuid: Callable) -> wcc.Selectors:
    """The options part of the menu"""
    options_uuid = get_uuid("options")
    return wcc.Selectors(
        id=get_uuid("options_layout"),
        label="Options",
        children=[
            html.Div(
                id={"id": options_uuid, "element": "statistical_options"},
                children=[
                    wcc.RadioItems(
                        id={"id": options_uuid, "element": "statistical_option"},
                        options=[
                            {"label": "Mean", "value": "mean"},
                            {"label": "P10 (high)", "value": "p10"},
                            {"label": "P50 (median)", "value": "p50"},
                            {"label": "P90 (low)", "value": "p90"},
                            {"label": "Maximum", "value": "max"},
                            {"label": "Minimum", "value": "min"},
                        ],
                    )
                ],
            ),
            html.Div(
                id={"id": options_uuid, "element": "single_real_options"},
                children=[
                    wcc.Dropdown(
                        label="Realization",
                        id={"id": options_uuid, "element": "realization"},
                        options=[],
                        value=None,
                        multi=False,
                    )
                ],
            ),
        ],
    )


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
        ],
    )
