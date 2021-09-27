from typing import Callable, Dict, List, Optional

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import html

from ..models import PropertyStatisticsModel
from .selector_view import ensemble_selector, filter_selector, source_selector


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


def timeseries_view(get_uuid: Callable, options: List[Dict]) -> html.Div:
    return html.Div(
        style={"height": "38vh"},
        children=[
            html.Div(
                children=[
                    wcc.Dropdown(
                        id=get_uuid("property-response-vector-select"),
                        options=options,
                        clearable=False,
                        placeholder="Select a vector from the list...",
                    ),
                ]
            ),
            wcc.Graph(
                id=get_uuid("property-response-vector-graph"),
                config={"displayModeBar": False},
                style={"height": "35vh"},
            ),
        ],
    )


def correlation_view(get_uuid: Callable) -> wcc.Graph:
    return wcc.Graph(
        style={"height": "78vh"},
        id=get_uuid("property-response-correlation-graph"),
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
            ),
        ]
    )


def selector_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
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
    vector_options: List[Dict],
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
                            children=timeseries_view(
                                get_uuid=get_uuid, options=vector_options
                            ),
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
