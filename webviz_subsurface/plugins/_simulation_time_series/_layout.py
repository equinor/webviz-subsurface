from typing import Callable, List, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from webviz_subsurface_components import ExpressionInfo

from .types import (
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)

from ..._providers import Frequency
from ..._utils.vector_calculator import get_custom_vector_definitions_from_expressions


# pylint: disable=too-few-public-methods
class LayoutElements:
    """
    Definition of names of HTML-elements in layout

    TODO: Consider ids as in AiO convention https://dash.plotly.com/all-in-one-components
    """

    GRAPH = "graph"
    GRAPH_DATA_HAS_CHANGED_TRIGGER = (
        "graph_data_has_changed_trigger"  # NOTE: To force re-render of graph
    )

    ENSEMBLES_DROPDOWN = "ensembles_dropdown"
    VECTOR_SELECTOR = "vector_selector"

    VECTOR_CALCULATOR = "vector_calculator"
    VECTOR_CALCULATOR_MODAL = "vector_calculator_modal"
    VECTOR_CALCULATOR_OPEN_BUTTON = "vector_calculator_open_button"
    VECTOR_CALCULATOR_EXPRESSIONS = "vector_calculator_expressions"
    VECTOR_CALCULATOR_EXPRESSIONS_OPEN_MODAL = (
        "vector_calculator_expressions_open_modal"
    )

    DELTA_ENSEMBLE_A_DROPDOWN = "delta_ensemble_A_dropdown"
    DELTA_ENSEMBLE_B_DROPDOWN = "delta_ensemble_B_dropdown"
    DELTA_ENSEMBLE_CREATE_BUTTON = "delta_ensemble_create_button"
    CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "created_delta_ensemble_names_table"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
        "created_delta_ensemble_names_table_column"
    )

    VISUALIZATION_RADIO_ITEMS = "visualization_radio_items"

    PLOT_FANCHART_OPTIONS_CHECKLIST = "plot_fanchart_options_checklist"
    PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot_statistics_options_checklist"
    PLOT_TRACE_OPTIONS_CHECKLIST = "plot_trace_options_checklist"

    RESAMPLING_FREQUENCY_DROPDOWN = "resampling_frequency_dropdown"


# pylint: disable = too-many-arguments
def main_layout(
    get_uuid: Callable,
    ensemble_names: List[str],
    vector_selector_data: list,
    vector_calculator_data: list,
    predefined_expressions: List[ExpressionInfo],
    disable_resampling_dropdown: bool,
    selected_resampling_frequency: Frequency,
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
                        vector_selector_data=vector_selector_data,
                        vector_calculator_data=vector_calculator_data,
                        predefined_expressions=predefined_expressions,
                        disable_resampling_dropdown=disable_resampling_dropdown,
                        selected_resampling_frequency=selected_resampling_frequency,
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
                        children=[
                            wcc.Graph(
                                style={"height": "85vh"},
                                id=get_uuid(LayoutElements.GRAPH),
                            ),
                            dcc.Store(
                                # NOTE:Used to trigger graph update callback if data has
                                # changed, i.e. no change of regular INPUT html-elements
                                id=get_uuid(
                                    LayoutElements.GRAPH_DATA_HAS_CHANGED_TRIGGER
                                ),
                                data=0,
                            ),
                        ],
                    )
                ],
            ),
        ],
    )


# pylint: disable = too-many-arguments
def __settings_layout(
    get_uuid: Callable,
    ensembles: List[str],
    vector_selector_data: list,
    vector_calculator_data: list,
    predefined_expressions: List[ExpressionInfo],
    disable_resampling_dropdown: bool,
    selected_resampling_frequency: Frequency,
    selected_visualization: VisualizationOptions,
    selected_vectors: Optional[List[str]] = None,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Selectors(
                label="Resampling frequency",
                children=[
                    wcc.Dropdown(
                        id=get_uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                        clearable=False,
                        disabled=disable_resampling_dropdown,
                        options=[
                            {
                                "label": frequency.value,
                                "value": frequency.value,
                            }
                            for frequency in Frequency
                        ],
                        value=selected_resampling_frequency,
                    ),
                    wcc.Label(
                        "NB: Disabled for presampled data",
                        style={"font-style": "italic"}
                        if disable_resampling_dropdown
                        else {"display": "none"},
                    ),
                ],
            ),
            wcc.Selectors(
                label="Ensembles",
                children=[
                    wcc.Dropdown(
                        label="Selected ensembles",
                        id=get_uuid(LayoutElements.ENSEMBLES_DROPDOWN),
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
                        id=get_uuid(LayoutElements.VECTOR_SELECTOR),
                        maxNumSelectedNodes=3,
                        data=vector_selector_data,
                        persistence=True,
                        persistence_type="session",
                        selectedTags=[]
                        if selected_vectors is None
                        else selected_vectors,
                        numSecondsUntilSuggestionsAreShown=0.5,
                        lineBreakAfterTag=True,
                        customVectorDefinitions=get_custom_vector_definitions_from_expressions(
                            predefined_expressions
                        ),
                    )
                ],
            ),
            wcc.Selectors(
                label="Visualization",
                children=[
                    wcc.RadioItems(
                        id=get_uuid(LayoutElements.VISUALIZATION_RADIO_ITEMS),
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
            wcc.Selectors(
                label="Vector Calculator",
                children=[
                    html.Button(
                        "Vector Calculator",
                        id=get_uuid(LayoutElements.VECTOR_CALCULATOR_OPEN_BUTTON),
                    ),
                ],
            ),
            __vector_calculator_modal_layout(
                get_uuid=get_uuid,
                vector_data=vector_calculator_data,
                predefined_expressions=predefined_expressions,
            ),
            dcc.Store(
                id=get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS),
                data=predefined_expressions,
            ),
            dcc.Store(
                id=get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_MODAL),
                data=predefined_expressions,
            ),
        ]
    )


def __vector_calculator_modal_layout(
    get_uuid: Callable,
    vector_data: list,
    predefined_expressions: List[ExpressionInfo],
) -> dbc.Modal:
    return dbc.Modal(
        style={"marginTop": "20vh", "width": "1300px"},
        children=[
            dbc.ModalHeader("Vector Calculator"),
            dbc.ModalBody(
                html.Div(
                    children=[
                        wsc.VectorCalculator(
                            id=get_uuid(LayoutElements.VECTOR_CALCULATOR),
                            vectors=vector_data,
                            expressions=predefined_expressions,
                        )
                    ],
                ),
            ),
        ],
        id=get_uuid(LayoutElements.VECTOR_CALCULATOR_MODAL),
        size="lg",
        centered=True,
    )


def __delta_ensemble_creator_layout(
    get_uuid: Callable, ensembles: List[str]
) -> html.Div:
    return html.Div(
        children=[
            wcc.Dropdown(
                label="Ensemble A",
                id=get_uuid(LayoutElements.DELTA_ENSEMBLE_A_DROPDOWN),
                clearable=False,
                options=[{"label": i, "value": i} for i in ensembles],
                value=ensembles[0],
                style={"min-width": "60px"},
            ),
            wcc.Dropdown(
                label="Ensemble B",
                id=get_uuid(LayoutElements.DELTA_ENSEMBLE_B_DROPDOWN),
                clearable=False,
                options=[{"label": i, "value": i} for i in ensembles],
                value=ensembles[-1],
                style={"min-width": "60px"},
            ),
            html.Button(
                "Create",
                id=get_uuid(LayoutElements.DELTA_ENSEMBLE_CREATE_BUTTON),
                n_clicks=0,
                style={
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                    "min-width": "20px",
                },
            ),
            __delta_ensemble_table_layout(get_uuid),
            dcc.Store(
                id=get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                data=[],
            ),  # TODO: Add predefined deltas?
        ]
    )


def __delta_ensemble_table_layout(get_uuid: Callable) -> dash_table.DataTable:
    return dash_table.DataTable(
        id=get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE),
        columns=(
            [
                {
                    "id": get_uuid(
                        LayoutElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
                    ),
                    "name": "Created Delta (A-B)",
                }
            ]
        ),
        data=[],
        fixed_rows={"headers": True},
        style_as_list_view=True,
        style_cell={"textAlign": "left"},
        style_header={"fontWeight": "bold"},
        style_table={
            "maxHeight": "150px",
            "overflowY": "auto",
        },
        editable=False,
    )


def __plot_options_layout(
    get_uuid: Callable,
    selected_visualization: VisualizationOptions,
) -> html.Div:
    return (
        html.Div(
            children=[
                wcc.Checklist(
                    id=get_uuid(LayoutElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                    options=[
                        {"label": "History", "value": TraceOptions.HISTORY.value},
                    ],
                    value=[TraceOptions.HISTORY.value],
                ),
                wcc.Checklist(
                    id=get_uuid(LayoutElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
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
                    id=get_uuid(LayoutElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
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
