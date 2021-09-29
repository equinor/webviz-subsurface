from typing import Callable

import webviz_core_components as wcc
from dash import html
from webviz_config import WebvizConfigTheme

from ..models import ParametersModel, SimulationTimeSeriesModel
from .selector_view import (
    color_opacity_selector,
    color_selector,
    date_selector,
    ensemble_selector,
    filter_vector_selector,
    parameter_selector,
    plot_options,
    vector_selector,
)


def timeseries_view(get_uuid: Callable) -> html.Div:
    return html.Div(
        children=[
            wcc.Graph(
                id=get_uuid("vector-vs-time-graph"),
                config={"displayModeBar": False},
                style={"height": "38vh"},
            ),
        ],
    )


def selector_view(
    get_uuid: Callable,
    vectormodel: SimulationTimeSeriesModel,
    parametermodel: ParametersModel,
    theme: WebvizConfigTheme,
) -> html.Div:

    theme_colors = theme.plotly_theme.get("layout", {}).get("colorway", [])
    theme_colors = (
        theme_colors[1:12] if theme_colors and len(theme_colors) >= 12 else theme_colors
    )

    return wcc.Frame(
        style={
            "height": "80vh",
            "overflowY": "auto",
            "font-size": "15px",
        },
        children=[
            wcc.Selectors(
                label="Selections",
                children=[
                    ensemble_selector(
                        get_uuid=get_uuid,
                        parametermodel=parametermodel,
                        tab="response",
                        id_string="ensemble-selector",
                        heading="Ensemble:",
                        value=parametermodel.ensembles[0],
                    ),
                    vector_selector(get_uuid=get_uuid, vectormodel=vectormodel),
                    date_selector(get_uuid=get_uuid, vectormodel=vectormodel),
                    parameter_selector(
                        get_uuid=get_uuid, parametermodel=parametermodel, tab="response"
                    ),
                ],
            ),
            wcc.Selectors(
                label="Filters",
                children=[
                    wcc.Checklist(
                        id=get_uuid("display-paramfilter"),
                        options=[{"label": "Show parameter filter", "value": "Show"}],
                        value=[],
                    ),
                    filter_vector_selector(
                        get_uuid=get_uuid, vectormodel=vectormodel, tab="response"
                    ),
                ],
            ),
            wcc.Selectors(
                label="Options",
                open_details=False,
                children=[
                    plot_options(get_uuid=get_uuid, tab="response"),
                    color_selector(
                        get_uuid=get_uuid,
                        tab="response",
                        colors=[theme_colors, "Greys", "BrBG"],
                        bargap=0.2,
                        height=50,
                    ),
                    color_opacity_selector(
                        get_uuid=get_uuid, tab="response", value=0.5
                    ),
                ],
            ),
        ],
    )


def parameter_response_view(
    get_uuid: Callable,
    parametermodel: ParametersModel,
    parameterfilter_layout: html.Div,
    vectormodel: SimulationTimeSeriesModel,
    theme: WebvizConfigTheme,
) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            wcc.FlexColumn(
                flex=1,
                children=selector_view(
                    get_uuid=get_uuid,
                    parametermodel=parametermodel,
                    vectormodel=vectormodel,
                    theme=theme,
                ),
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.FlexBox(
                    children=[
                        wcc.FlexColumn(
                            flex=2,
                            children=[
                                wcc.Frame(
                                    style={"height": "38.5vh"},
                                    color="white",
                                    highlight=False,
                                    children=timeseries_view(get_uuid=get_uuid),
                                ),
                                wcc.Frame(
                                    style={"height": "38.5vh"},
                                    color="white",
                                    highlight=False,
                                    children=[
                                        wcc.Graph(
                                            id=get_uuid("vector-vs-param-scatter"),
                                            config={"displayModeBar": False},
                                            style={"height": "38vh"},
                                        )
                                    ],
                                ),
                            ],
                        ),
                        wcc.FlexColumn(
                            flex=2,
                            children=[
                                wcc.Frame(
                                    color="white",
                                    highlight=False,
                                    style={"height": "38.5vh"},
                                    children=[
                                        wcc.Graph(
                                            config={"displayModeBar": False},
                                            style={"height": "38vh"},
                                            id=get_uuid("vector-corr-graph"),
                                        ),
                                    ],
                                ),
                                wcc.Frame(
                                    color="white",
                                    highlight=False,
                                    style={"height": "38.5vh"},
                                    children=[
                                        wcc.Graph(
                                            config={"displayModeBar": False},
                                            style={"height": "38vh"},
                                            id=get_uuid("param-corr-graph"),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        wcc.FlexColumn(
                            id=get_uuid("param-filter-wrapper"),
                            style={"display": "none"},
                            flex=1,
                            children=wcc.Frame(
                                style={"height": "80vh"},
                                children=parameterfilter_layout,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )
