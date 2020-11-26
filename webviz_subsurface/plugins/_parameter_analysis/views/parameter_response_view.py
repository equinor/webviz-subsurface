import dash_html_components as html
import webviz_core_components as wcc
from .selector_view import (
    ensemble_selector,
    filter_vector_selector,
    vector_selector,
    parameter_selector,
    date_selector,
    plot_options,
    html_details,
    color_selector,
    color_opacity_selector,
)


def timeseries_view(parent) -> html.Div:
    return html.Div(
        children=[
            wcc.Graph(
                id=parent.uuid("vector-vs-time-graph"),
                config={"displayModeBar": False},
                style={"height": "38vh"},
            ),
        ],
    )


def selector_view(parent) -> html.Div:

    return html.Div(
        style={
            "height": "80vh",
            "overflowY": "auto",
            "font-size": "15px",
        },
        className="framed",
        children=[
            html_details(
                summary="Selections",
                children=[
                    ensemble_selector(
                        parent=parent,
                        tab="response",
                        id_string="ensemble-selector",
                        heading="Ensemble:",
                        value=parent.pmodel.ensembles[0],
                    ),
                    vector_selector(parent=parent),
                    date_selector(parent=parent),
                    parameter_selector(parent=parent, tab="response"),
                ],
                open_details=True,
            ),
            html_details(
                summary=[
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
                children=[filter_vector_selector(parent=parent, tab="response")],
                open_details=False,
            ),
            html_details(
                summary="Options",
                children=[
                    plot_options(parent=parent, tab="response"),
                    color_selector(
                        parent=parent,
                        tab="response",
                        px_colors={"sequential": ["Greys"], "diverging": ["BrBG"]},
                        height=60,
                    ),
                    color_opacity_selector(parent=parent, tab="response", value=0.5),
                ],
                open_details=False,
            ),
        ],
    )


def parameter_response_view(parent) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"margin": "20px"},
        children=[
            html.Div(
                style={"flex": 1, "width": "90%"},
                children=selector_view(parent=parent),
            ),
            html.Div(
                style={"flex": 2, "height": "80vh"},
                children=[
                    html.Div(
                        className="framed",
                        style={"height": "37.5vh"},
                        children=timeseries_view(parent=parent),
                    ),
                    html.Div(
                        className="framed",
                        style={"height": "37.5vh"},
                        children=[
                            wcc.Graph(
                                id=parent.uuid("vector-vs-param-scatter"),
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                            )
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"flex": 2, "height": "80vh"},
                children=[
                    html.Div(
                        className="framed",
                        style={"height": "37.5vh"},
                        children=[
                            wcc.Graph(
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                                id=parent.uuid("vector-corr-graph"),
                            ),
                        ],
                    ),
                    html.Div(
                        className="framed",
                        style={"height": "37.5vh"},
                        children=[
                            wcc.Graph(
                                config={"displayModeBar": False},
                                style={"height": "38vh"},
                                id=parent.uuid("param-corr-graph"),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
