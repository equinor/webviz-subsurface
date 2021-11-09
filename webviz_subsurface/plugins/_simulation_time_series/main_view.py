from typing import Callable, List, Optional

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import webviz_core_components as wcc
import webviz_subsurface_components as wsc

from .types import (
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)


# pylint: disable=too-few-public-methods
class ViewElements:
    """
    Definition of names of HTML-elements in view

    TODO: Consider ids as in AiO convention https://dash.plotly.com/all-in-one-components
    """

    GRAPH = "graph"

    ENSEMBLES_DROPDOWN = "ensembles_dropdown"
    VECTOR_SELECTOR = "vector_selector"

    DELTA_ENSEMBLE_A_DROPDOWN = "delta_ensemble_A_dropdown"
    DELTA_ENSEMBLE_B_DROPDOWN = "delta_ensemble_B_dropdown"
    DELTA_ENSEMBLE_ADD_BUTTON = "delta_ensemble_add_button"
    CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "created_delta_ensemble_names_table"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
        "created_delta_ensemble_names_table_column"
    )

    VISUALIZATION_RADIO_ITEMS = "visualization_radio_items"

    PLOT_FANCHART_OPTIONS_CHECKLIST = "plot_fanchart_options_checklist"
    PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot_statistics_options_checklist"
    PLOT_TRACE_OPTIONS_CHECKLIST = "plot_trace_options_checklist"


def main_view(
    get_uuid: Callable,
    ensemble_names: List[str],
    vector_selector_data: list,
    selected_visualization: VisualizationOptions,
    selected_vectors: Optional[List[str]] = None,
) -> html.Div:
    return wcc.FlexBox(
        children=[
            # Settings layout
            wcc.FlexColumn(
                children=wcc.Frame(
                    style={"height": "90vh"},
                    children=__settings_layout(
                        get_uuid=get_uuid,
                        ensembles=ensemble_names,
                        vector_data=vector_selector_data,
                        selected_visualization=selected_visualization,
                        selected_vectors=selected_vectors,
                    ),
                )
            ),
            # Graph layout
            wcc.FlexColumn(
                flex=4,
                children=[
                    wcc.Frame(
                        style={"height": "90vh"},
                        highlight=False,
                        color="white",
                        children=wcc.Graph(
                            style={"height": "85vh"},
                            id=get_uuid(ViewElements.GRAPH),
                        ),
                    )
                ],
            ),
        ],
    )


def __settings_layout(
    get_uuid: Callable,
    ensembles: List[str],
    vector_data: list,
    selected_visualization: VisualizationOptions,
    selected_vectors: Optional[List[str]] = None,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Selectors(
                label="Ensembles",
                children=[
                    wcc.Dropdown(
                        label="Selected ensembles",
                        id=get_uuid(ViewElements.ENSEMBLES_DROPDOWN),
                        clearable=False,
                        multi=True,
                        options=[
                            {"label": ensemble, "value": ensemble}
                            for ensemble in ensembles
                        ],
                        value=None if len(ensembles) <= 0 else [ensembles[0]],
                    ),
                    wcc.Selectors(
                        label="Delta Ensembles",
                        children=[
                            __delta_ensemble_creator_layout(
                                get_uuid=get_uuid,
                                ensembles=ensembles,
                            )
                        ],
                    ),
                ],
            ),
            wcc.Selectors(
                label="Time Series",
                children=[
                    wsc.VectorSelector(
                        id=get_uuid(ViewElements.VECTOR_SELECTOR),
                        maxNumSelectedNodes=3,
                        data=vector_data,
                        persistence=True,
                        persistence_type="session",
                        selectedTags=[]
                        if selected_vectors is None
                        else selected_vectors,
                        numSecondsUntilSuggestionsAreShown=0.5,
                        lineBreakAfterTag=True,
                    )
                ],
            ),
            wcc.Selectors(
                label="Visualization",
                children=[
                    wcc.RadioItems(
                        id=get_uuid(ViewElements.VISUALIZATION_RADIO_ITEMS),
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
                                "label": "Statistical fanchart",
                                "value": VisualizationOptions.FANCHART.value,
                            },
                        ],
                        value=selected_visualization.value,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Options",
                children=__plot_options_layout(
                    get_uuid=get_uuid,
                    selected_visualization=selected_visualization,
                ),
            ),
        ]
    )


def __delta_ensemble_creator_layout(
    get_uuid: Callable, ensembles: List[str]
) -> html.Div:
    return html.Div(
        children=[
            wcc.FlexBox(
                children=[
                    wcc.FlexColumn(
                        min_width="60px",
                        children=wcc.Dropdown(
                            label="Ensemble A",
                            id=get_uuid(ViewElements.DELTA_ENSEMBLE_A_DROPDOWN),
                            clearable=False,
                            options=[{"label": i, "value": i} for i in ensembles],
                            value=ensembles[0],
                        ),
                    ),
                    wcc.FlexColumn(
                        min_width="60px",
                        children=wcc.Dropdown(
                            label="Ensemble B",
                            id=get_uuid(ViewElements.DELTA_ENSEMBLE_B_DROPDOWN),
                            clearable=False,
                            options=[{"label": i, "value": i} for i in ensembles],
                            value=ensembles[-1],
                        ),
                    ),
                    wcc.FlexColumn(
                        min_width="20px",
                        children=html.Button(
                            "Add",
                            id=get_uuid(ViewElements.DELTA_ENSEMBLE_ADD_BUTTON),
                            n_clicks=0,
                        ),
                    ),
                ],
                style={"align-items": "flex-end"},
            ),
            dash_table.DataTable(
                id=get_uuid(ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE),
                columns=(
                    [
                        {
                            "id": get_uuid(
                                ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
                            ),
                            "name": "Created Delta (A-B)",
                        }
                    ]
                ),
                data=[],
                fixed_rows={"headers": True},
                style_as_list_view=True,
                style_cell={"textAlign": "left"},
                style_table={
                    "maxHeight": "150px",
                    "overflowY": "auto",
                },
                editable=False,
            ),
            dcc.Store(
                id=get_uuid(ViewElements.CREATED_DELTA_ENSEMBLES),
                data=[],
            ),  # TODO: Add predefined deltas?
        ]
    )


def __plot_options_layout(
    get_uuid: Callable,
    selected_visualization: VisualizationOptions,
) -> html.Div:
    return (
        html.Div(
            children=[
                wcc.Checklist(
                    id=get_uuid(ViewElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                    options=[
                        {"label": "History", "value": TraceOptions.HISTORY.value},
                        {
                            "label": "Vector observations",
                            "value": TraceOptions.VECTOR_OBSERVATIONS.value,
                        },
                    ],
                    value=[
                        TraceOptions.HISTORY.value,
                        TraceOptions.VECTOR_OBSERVATIONS.value,
                    ],
                ),
                wcc.Checklist(
                    id=get_uuid(ViewElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                    style={"display": "block"}
                    if VisualizationOptions.STATISTICS == selected_visualization
                    else {"display": "none"},
                    options=[
                        {"label": "Mean", "value": StatisticsOptions.MEAN.value},
                        {
                            "label": "P10 (high)",
                            "value": StatisticsOptions.P10.value,
                        },
                        {
                            "label": "P50 (median)",
                            "value": StatisticsOptions.P50.value,
                        },
                        {
                            "label": "P90 (low)",
                            "value": StatisticsOptions.P90.value,
                        },
                        {"label": "Maximum", "value": StatisticsOptions.MAX.value},
                        {"label": "Minimum", "value": StatisticsOptions.MIN.value},
                    ],
                    value=[
                        StatisticsOptions.MEAN.value,
                        StatisticsOptions.P10.value,
                        StatisticsOptions.P90.value,
                    ],
                ),
                wcc.Checklist(
                    id=get_uuid(ViewElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
                    style={"display": "block"}
                    if VisualizationOptions.FANCHART == selected_visualization
                    else {"display": "none"},
                    options=[
                        {
                            "label": FanchartOptions.MEAN.value,
                            "value": FanchartOptions.MEAN.value,
                        },
                        {
                            "label": FanchartOptions.P10_P90.value,
                            "value": FanchartOptions.P10_P90.value,
                        },
                        {
                            "label": FanchartOptions.MIN_MAX.value,
                            "value": FanchartOptions.MIN_MAX.value,
                        },
                    ],
                    value=[
                        FanchartOptions.MEAN.value,
                        FanchartOptions.P10_P90.value,
                        FanchartOptions.MIN_MAX.value,
                    ],
                ),
            ],
        ),
    )
