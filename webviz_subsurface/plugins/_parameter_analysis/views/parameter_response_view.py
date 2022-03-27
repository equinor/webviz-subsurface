from enum import Enum
from typing import Callable

import webviz_core_components as wcc
from dash import html
from webviz_config import WebvizConfigTheme

from webviz_subsurface._components.parameter_filter import ParameterFilter

from ..models import ParametersModel, SimulationTimeSeriesModel
from .selector_view import (
    button,
    color_opacity_selector,
    color_selector,
    date_selector,
    ensemble_selector,
    filter_vector_selector,
    parameter_selector,
    plot_options,
    vector_selector,
)


class VisualizationOptions(str, Enum):
    """
    Type definition for visualization options in simulation time series
    """

    REALIZATIONS = "realizations"
    STATISTICS = "statistics"
    STATISTICS_AND_REALIZATIONS = "statistics and realizations"


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
) -> wcc.Frame:

    theme_colors = theme.plotly_theme.get("layout", {}).get("colorway", [])
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
                        ensembles=parametermodel.mc_ensembles,
                        tab="response",
                        id_string="ensemble-selector",
                        heading="Ensemble:",
                    ),
                    vector_selector(get_uuid=get_uuid, vectormodel=vectormodel),
                    date_selector(get_uuid=get_uuid, vectormodel=vectormodel),
                    parameter_selector(
                        get_uuid=get_uuid, parametermodel=parametermodel, tab="response"
                    ),
                ],
            ),
            wcc.Selectors(
                label="Visualization",
                children=[
                    wcc.RadioItems(
                        id=get_uuid("visualization"),
                        options=[
                            {
                                "label": "Individual realizations",
                                "value": VisualizationOptions.REALIZATIONS.value,
                            },
                            {
                                "label": "Statistical lines",
                                "value": VisualizationOptions.STATISTICS.value,
                            },
                            {
                                "label": "Statistics + Realizations",
                                "value": VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                            },
                        ],
                        value=VisualizationOptions.REALIZATIONS.value,
                    )
                ],
            ),
            wcc.Selectors(
                label="Vectors for parameter correlation",
                children=filter_vector_selector(get_uuid=get_uuid),
            ),
            wcc.Selectors(
                label="Options",
                children=[
                    parameter_filter_button(get_uuid),
                    options_layout(get_uuid, theme_colors),
                ],
            ),
        ],
    )


def parameter_filter_button(get_uuid: Callable):
    return button(get_uuid("display-paramfilter"), "Show parameter filter")


def options_layout(get_uuid: Callable, theme_colors: list):
    return html.Div(
        children=[
            button(get_uuid("options-button"), "Options"),
            wcc.Dialog(
                title="Options",
                id=get_uuid("options-dialog"),
                backdrop=False,
                draggable=True,
                open=False,
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
        ]
    )


def parameter_response_view(
    get_uuid: Callable,
    parametermodel: ParametersModel,
    vectormodel: SimulationTimeSeriesModel,
    theme: WebvizConfigTheme,
) -> wcc.FlexBox:
    df = parametermodel.dataframe
    parameter_filter = ParameterFilter(
        uuid=get_uuid("parameter-filter"),
        dframe=df[df["ENSEMBLE"].isin(parametermodel.mc_ensembles)].copy(),
        reset_on_ensemble_update=True,
    )
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
                                children=parameter_filter.layout,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )
