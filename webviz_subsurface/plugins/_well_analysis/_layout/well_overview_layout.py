from typing import Callable, Dict

import webviz_core_components as wcc
from dash import html

from .._ensemble_data import EnsembleWellAnalysisData


# pylint: disable = too-few-public-methods
class WellOverviewLayoutElements:
    GRAPH = "well-overview-graph"
    ENSEMBLES = "well-overview-ensembles"
    SUMVEC = "well-overview-sumvec"
    CHARTTYPE_BUTTON = "well-overview-charttype-button"
    CHARTTYPE_SETTINGS = "well-overview-charttype-settings"
    CHARTTYPE_CHECKLIST = "well-overview-charttype-checklist"


def well_overview_tab(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.FlexBox:
    """Well overview tab"""
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1, "height": "87vh"},
                children=[
                    buttons(get_uuid),
                    controls(get_uuid, data_models),
                    plot_settings(get_uuid, data_models),
                ],
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


def buttons(get_uuid: Callable) -> html.Div:
    uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_BUTTON)
    return html.Div(
        style={"margin-bottom": "20px"},
        children=[
            html.Button(
                "Bar Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": "bar"},
            ),
            html.Button(
                "Pie Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": "pie"},
            ),
            html.Button(
                "Stacked Area Chart",
                className="webviz-inplace-vol-btn",
                id={"id": uuid, "button": "area"},
            ),
        ],
    )


def controls(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Frame:
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
            wcc.Dropdown(
                label="Response",
                id=get_uuid(WellOverviewLayoutElements.SUMVEC),
                options=[
                    {"label": "Oil production", "value": "WOPT"},
                    {"label": "Gas production", "value": "WGPT"},
                    {"label": "Water production", "value": "WWPT"},
                ],
                value="WOPT",
                multi=False,
            ),
        ],
    )


def plot_settings(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Frame:
    settings_uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_SETTINGS)
    checklist_uuid = get_uuid(WellOverviewLayoutElements.CHARTTYPE_CHECKLIST)
    return wcc.Selectors(
        label="Plot Settings",
        children=[
            html.Div(
                id={"id": settings_uuid, "charttype": "bar"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "bar"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "Overlay bars", "value": "overlay_bars"},
                    ],
                    value=["legend"],
                ),
            ),
            html.Div(
                id={"id": settings_uuid, "charttype": "pie"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "pie"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                    ],
                    value=[],
                ),
            ),
            html.Div(
                id={"id": settings_uuid, "charttype": "area"},
                children=wcc.Checklist(
                    id={"id": checklist_uuid, "charttype": "area"},
                    options=[
                        {"label": "Show legend", "value": "legend"},
                    ],
                    value=["legend"],
                ),
            ),
        ],
    )
