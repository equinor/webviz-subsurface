from typing import TYPE_CHECKING

import dash_html_components as html
import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from .selector_view import (
    ensemble_selector,
    filter_selector,
    source_selector,
)

if TYPE_CHECKING:
    # pylint: disable=cyclic-import
    from ..property_statistics import PropertyStatistics


def surface_select_view(parent: "PropertyStatistics", tab: str) -> html.Div:
    return html.Div(
        id=parent.uuid("surface-select"),
        style={"width": "75%"},
        children=wcc.Dropdown(
            label="Surface statistics",
            id={"id": parent.uuid("surface-type"), "tab": tab},
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


def surface_view(parent: "PropertyStatistics", tab: str) -> html.Div:
    return html.Div(
        style={"height": "35vh"},
        children=[
            wcc.Label(
                id={"id": parent.uuid("surface-name"), "tab": tab},
                children="Select vector, then click on a correlation to visualize surface",
            ),
            wsc.LeafletMap(
                id={"id": parent.uuid("surface-view"), "tab": tab},
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


def timeseries_view(parent: "PropertyStatistics") -> html.Div:
    return html.Div(
        style={"height": "38vh"},
        children=[
            html.Div(
                children=[
                    wcc.Dropdown(
                        id=parent.uuid("property-response-vector-select"),
                        options=parent.vmodel.dropdown_options,
                        clearable=False,
                        placeholder="Select a vector from the list...",
                    ),
                ]
            ),
            wcc.Graph(
                id=parent.uuid("property-response-vector-graph"),
                config={"displayModeBar": False},
                style={"height": "35vh"},
            ),
        ],
    )


def correlation_view(parent: "PropertyStatistics") -> wcc.Graph:
    return wcc.Graph(
        style={"height": "78vh"},
        id=parent.uuid("property-response-correlation-graph"),
    )


def filter_correlated_parameter(parent: "PropertyStatistics") -> html.Div:
    return html.Div(
        [
            html.Div(
                style={"marginBottom": "10px"},
                children=wcc.Dropdown(
                    label="Filter on property",
                    id=parent.uuid("property-response-correlated-filter"),
                    options=[
                        {"label": label, "value": label}
                        for label in parent.pmodel.get_labels()
                    ],
                    placeholder="Select a label to filter on...",
                ),
            ),
            wcc.RangeSlider(
                id=parent.uuid("property-response-correlated-slider"),
                disabled=True,
            ),
        ]
    )


def selector_view(parent: "PropertyStatistics") -> html.Div:
    return html.Div(
        children=[
            wcc.Selectors(
                label="Selectors",
                children=[
                    ensemble_selector(parent=parent, tab="response"),
                    source_selector(parent=parent, tab="response"),
                ],
            ),
            wcc.Selectors(
                label="Filters",
                children=[
                    filter_selector(parent=parent, tab="response"),
                    filter_correlated_parameter(parent=parent),
                ],
            ),
            wcc.Selectors(
                label="Surface",
                children=[surface_select_view(parent=parent, tab="response")]
                if parent.surface_folders is not None
                else [html.Div()],
            ),
        ],
    )


def property_response_view(parent: "PropertyStatistics") -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=wcc.Frame(
                    style={"height": "80vh", "overflowY": "auto"},
                    children=selector_view(parent=parent),
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
                            children=timeseries_view(parent=parent),
                        ),
                        html.Div(
                            style={"height": "39vh"},
                            children=surface_view(parent=parent, tab="response")
                            if parent.surface_folders is not None
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
                    children=correlation_view(parent=parent),
                ),
            ),
        ],
    )
