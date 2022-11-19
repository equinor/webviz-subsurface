from typing import Callable, Dict, List, Optional, Union

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import html

from ..models import (
    PropertyStatisticsModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)
from .selector_view import (
    ensemble_selector,
    filter_selector,
    source_selector,
    vector_selector,
)


def surface_select_view(get_uuid: Callable, tab: str) -> html.Div:
    return html.Div(
        id=get_uuid("surface-select"),
        style={"width": "75%"},
        children=wcc.Dropdown(
            label="Surface statistics",
            id={"id": get_uuid("surface-type"), "tab": tab},
            options=[
                {"label": "Mean", "value": "mean"},
                {"label": "Standard Deviation", "value": "stddev"},
                {"label": "Minimum", "value": "min"},
                {"label": "Maximum", "value": "max"},
                {"label": "P10", "value": "p10"},
                {"label": "P90", "value": "p90"},
            ],
            clearable=False,
            value="mean",
        ),
    )


def surface_view(get_uuid: Callable, tab: str) -> html.Div:
    return html.Div(
        style={"height": "35vh"},
        children=[
            wcc.Label(
                id={"id": get_uuid("surface-name"), "tab": tab},
                children="Select vector, then click on a correlation to visualize surface",
            ),
            wsc.LeafletMap(
                id={"id": get_uuid("surface-view"), "tab": tab},
                layers=[],
                unitScale={},
                autoScaleMap=True,
                minZoom=-19,
                updateMode="update",
                mouseCoords={"position": "bottomright"},
                colorBar={"position": "bottomleft"},
            ),
        ],
    )


def timeseries_view(get_uuid: Callable) -> html.Div:
    return html.Div(
        style={"height": "38vh"},
        children=[
            wcc.Graph(
                id=get_uuid("property-response-vector-graph"),
                config={"displayModeBar": False},
                style={"height": "35vh"},
            ),
        ],
    )


def correlation_view(get_uuid: Callable) -> wcc.Graph:
    return html.Div(
        [
            wcc.Graph(
                style={"height": "38vh"},
                id=get_uuid("property-response-correlation-graph"),
            ),
            wcc.Graph(
                style={"height": "38vh", "margin-top": "20px"},
                id=get_uuid("property-response-scatter-graph"),
            ),
        ]
    )


def filter_correlated_parameter(get_uuid: Callable, labels: List[str]) -> html.Div:
    return html.Div(
        [
            html.Div(
                style={"marginBottom": "10px"},
                children=wcc.Dropdown(
                    label="Filter on property",
                    id=get_uuid("property-response-correlated-filter"),
                    options=[{"label": label, "value": label} for label in labels],
                    placeholder="Select a label to filter on...",
                ),
            ),
            wcc.RangeSlider(
                id=get_uuid("property-response-correlated-slider"),
                disabled=True,
                marks=None,
            ),
        ]
    )


def selector_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    vector_model: Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel],
    surface_folders: Optional[Dict],
) -> html.Div:
    return html.Div(
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    ensemble_selector(
                        get_uuid=get_uuid,
                        ensembles=property_model.ensembles,
                        tab="response",
                    ),
                    source_selector(
                        get_uuid=get_uuid,
                        sources=property_model.sources,
                        tab="response",
                    ),
                    vector_selector(get_uuid=get_uuid, vector_model=vector_model),
                ],
            ),
            wcc.Selectors(
                label="Filters",
                children=[
                    filter_selector(
                        get_uuid=get_uuid, property_model=property_model, tab="response"
                    ),
                    filter_correlated_parameter(
                        get_uuid=get_uuid, labels=property_model.get_labels()
                    ),
                ],
            ),
            wcc.Selectors(
                label="Surface",
                children=[surface_select_view(get_uuid=get_uuid, tab="response")]
                if surface_folders is not None
                else [html.Div()],
            ),
        ],
    )


def property_response_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    vector_model: Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel],
    surface_folders: Optional[Dict],
) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=wcc.Frame(
                    style={"height": "80vh", "overflowY": "auto"},
                    children=selector_view(
                        get_uuid=get_uuid,
                        property_model=property_model,
                        vector_model=vector_model,
                        surface_folders=surface_folders,
                    ),
                )
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    style={"height": "80vh"},
                    color="white",
                    highlight=False,
                    children=[
                        html.Div(
                            style={"height": "38vh"},
                            children=timeseries_view(get_uuid=get_uuid),
                        ),
                        html.Div(
                            style={"height": "39vh"},
                            children=surface_view(get_uuid=get_uuid, tab="response")
                            if surface_folders is not None
                            else None,
                        ),
                    ],
                ),
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.Frame(
                    style={"height": "80vh"},
                    color="white",
                    highlight=False,
                    children=correlation_view(get_uuid=get_uuid),
                ),
            ),
        ],
    )
