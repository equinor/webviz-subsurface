from typing import Callable, List, Optional

import dash_bootstrap_components as dbc
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dash_table, dcc, html
from webviz_subsurface_components import ExpressionInfo

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.vector_calculator import (
    get_custom_vector_definitions_from_expressions,
)

from .types import (
    FanchartOptions,
    StatisticsFromOptions,
    StatisticsOptions,
    SubplotGroupByOptions,
    TraceOptions,
    VisualizationOptions,
)


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

    SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS = "subplot_owner_options_radio_items"

    RESAMPLING_FREQUENCY_DROPDOWN = "resampling_frequency_dropdown"

    REALIZATIONS_FILTER_OPTION = "realizations_filter_option"
    REALIZATIONS_FILTER_SELECTOR = "realizations_filter_selector"
    REALIZATIONS_FILTER_SLIDER = "realizations_filter_slider"
    REALIZATIONS_FILTER_SPAN = "realizations_filter_span"
    STATISTICS_FROM_RADIO_ITEMS = "statistics_from_radio_items"

    TOUR_STEP_MAIN_LAYOUT = "tour_step_main_layout"
    TOUR_STEP_SETTINGS_LAYOUT = "tour_step_settings_layout"
    TOUR_STEP_GROUP_BY = "tour_step_group_by"
    TOUR_STEP_DELTA_ENSEMBLE = "tour_step_delta_ensemble"
    TOUR_STEP_OPTIONS = "tour_step_options"


# pylint: disable = too-many-arguments
def main_layout(
    get_uuid: Callable,
    ensemble_names: List[str],
    vector_selector_data: list,
    vector_calculator_data: list,
    predefined_expressions: List[ExpressionInfo],
    realizations: List[int],
    disable_resampling_dropdown: bool,
    selected_resampling_frequency: Frequency,
    selected_visualization: VisualizationOptions,
    selected_vectors: Optional[List[str]] = None,
) -> html.Div:
    return wcc.FlexBox(
        id=get_uuid(LayoutElements.TOUR_STEP_MAIN_LAYOUT),
        children=[
            # Settings layout
            wcc.FlexColumn(
                id=get_uuid(LayoutElements.TOUR_STEP_SETTINGS_LAYOUT),
                children=wcc.Frame(
                    style={"height": "90vh"},
                    children=__settings_layout(
                        get_uuid=get_uuid,
                        ensembles=ensemble_names,
                        vector_selector_data=vector_selector_data,
                        vector_calculator_data=vector_calculator_data,
                        predefined_expressions=predefined_expressions,
                        realizations=realizations,
                        disable_resampling_dropdown=disable_resampling_dropdown,
                        selected_resampling_frequency=selected_resampling_frequency,
                        selected_visualization=selected_visualization,
                        selected_vectors=selected_vectors,
                    ),
                ),
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
    realizations: List[int],
    disable_resampling_dropdown: bool,
    selected_resampling_frequency: Frequency,
    selected_visualization: VisualizationOptions,
    selected_vectors: Optional[List[str]] = None,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Selectors(
                label="Group By",
                id=get_uuid(LayoutElements.TOUR_STEP_GROUP_BY),
                children=[
                    wcc.RadioItems(
                        id=get_uuid(LayoutElements.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS),
                        options=[
                            {
                                "label": "Time Series",
                                "value": SubplotGroupByOptions.VECTOR.value,
                            },
                            {
                                "label": "Ensemble",
                                "value": SubplotGroupByOptions.ENSEMBLE.value,
                            },
                        ],
                        value=SubplotGroupByOptions.VECTOR.value,
                    ),
                ],
            ),
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
                        id=get_uuid(LayoutElements.TOUR_STEP_DELTA_ENSEMBLE),
                        open_details=False,
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
                    ),
                    html.Button(
                        "Vector Calculator",
                        id=get_uuid(LayoutElements.VECTOR_CALCULATOR_OPEN_BUTTON),
                        style={
                            "margin-top": "5px",
                            "margin-bottom": "5px",
                        },
                    ),
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
                            {
                                "label": "Statistics + Realizations",
                                "value": VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                            },
                        ],
                        value=selected_visualization.value,
                    ),
                    wcc.Selectors(
                        label="Options",
                        id=get_uuid(LayoutElements.TOUR_STEP_OPTIONS),
                        children=__plot_options_layout(
                            get_uuid=get_uuid,
                            selected_visualization=selected_visualization,
                        ),
                    ),
                ],
            ),
            wcc.Selectors(
                label="Filter Realizations",
                children=__realization_filters(get_uuid, realizations),
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


def __realization_filters(get_uuid: Callable, realizations: List[int]) -> html.Div:
    return html.Div(
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Label(
                        "Realizations: ",
                        style={"font-weight": "bold"},
                    ),
                    html.Label(
                        id=get_uuid(LayoutElements.REALIZATIONS_FILTER_SPAN),
                        style={
                            "margin-left": "10px",
                            "margin-bottom": "5px",
                        },
                        children=f"{min(realizations)}-{max(realizations)}",
                    ),
                ],
            ),
            wcc.RadioItems(
                label="Statistics calculated from:",
                id=get_uuid(LayoutElements.STATISTICS_FROM_RADIO_ITEMS),
                style={"margin-bottom": "10px"},
                options=[
                    {
                        "label": "All",
                        "value": StatisticsFromOptions.ALL_REALIZATIONS.value,
                    },
                    {
                        "label": "Selected",
                        "value": StatisticsFromOptions.SELECTED_REALIZATIONS.value,
                    },
                ],
                value=StatisticsFromOptions.ALL_REALIZATIONS.value,
                vertical=False,
            ),
            html.Div(
                children=wcc.Select(
                    id=get_uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR),
                    options=[{"label": i, "value": i} for i in realizations],
                    value=realizations,
                    size=min(10, len(realizations)),
                ),
            ),
        ],
    )


def __plot_options_layout(
    get_uuid: Callable,
    selected_visualization: VisualizationOptions,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Checklist(
                id=get_uuid(LayoutElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                options=[
                    {"label": "History", "value": TraceOptions.HISTORY.value},
                    {
                        "label": "Observation",
                        "value": TraceOptions.OBSERVATIONS.value,
                    },
                ],
                value=[TraceOptions.HISTORY.value, TraceOptions.OBSERVATIONS.value],
            ),
            wcc.Checklist(
                id=get_uuid(LayoutElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                style={"display": "block"}
                if selected_visualization
                in [
                    VisualizationOptions.STATISTICS,
                    VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                ]
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
    )
