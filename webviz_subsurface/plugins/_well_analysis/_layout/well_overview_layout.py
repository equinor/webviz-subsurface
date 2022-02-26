from typing import Callable, Dict

import webviz_core_components as wcc
from dash import html

from .._ensemble_data import EnsembleWellAnalysisData


# pylint: disable = too-few-public-methods
class WellOverviewLayoutElements:
    GRAPH = "well-overview-graph"
    ENSEMBLES = "well-overview-ensembles"
    OVERLAY_BARS = "well-overview-overlay-bars"
    SUMVEC = "well-overview-sumvec"
    CHARTTYPE_BUTTON = "well-overview-charttype-button"


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
    return wcc.Selectors(
        label="Plot Settings",
        children=[
            wcc.Checklist(
                id=get_uuid(WellOverviewLayoutElements.OVERLAY_BARS),
                options=[{"label": "Overlay bars", "value": "overlay_bars"}],
                value=[],
            ),
        ],
    )
