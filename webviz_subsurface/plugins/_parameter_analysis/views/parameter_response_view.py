from typing import Callable

from webviz_config import WebvizConfigTheme
import dash_html_components as html
import webviz_core_components as wcc

from .selector_view import (
    ensemble_selector,
    filter_vector_selector,
    vector_selector,
    parameter_selector,
    date_selector,
    plot_options,
    color_selector,
    color_opacity_selector,
)
from ..models import ParametersModel, SimulationTimeSeriesModel


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
                label=[
                    "Filters ",
                    html.Span(
                        "(for correlations)",
                        style={
                            "float": "right",
                            "margin-top": "10px",
                            "fontSize": "13px",
                            "font-weight": "normal",
                        },
                    ),
                ],
                children=[
                    filter_vector_selector(
                        get_uuid=get_uuid, vectormodel=vectormodel, tab="response"
                    )
                ],
            ),
            wcc.Selectors(
                label="Options",
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
    vectormodel: SimulationTimeSeriesModel,
    theme: WebvizConfigTheme,
) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            wcc.FlexColumn(
                children=selector_view(
                    get_uuid=get_uuid,
                    parametermodel=parametermodel,
                    vectormodel=vectormodel,
                    theme=theme,
                ),
            ),
            wcc.FlexColumn(
                flex=2,
                style={"height": "80vh"},
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
                style={"height": "80vh"},
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
        ],
    )
