# pylint: disable=too-many-lines
import copy
import datetime
from typing import Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config._theme_class import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
from webviz_subsurface_components import (
    ExpressionInfo,
    ExternalParseData,
    VectorDefinition,
)

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.formatting import printable_int_list
from webviz_subsurface._utils.vector_calculator import (
    add_expressions_to_vector_selector_data,
    get_selected_expressions,
    get_vector_definitions_from_expressions,
)
from webviz_subsurface._utils.vector_selector import (
    is_vector_name_in_vector_selector_data,
)

from ._plugin_ids import PluginIds
from .types import (
    DeltaEnsemble,
    FanchartOptions,
    ProviderSet,
    StatisticsFromOptions,
    StatisticsOptions,
    SubplotGroupByOptions,
    TraceOptions,
    VisualizationOptions,
)
from .utils import datetime_utils
from .utils.delta_ensemble_utils import create_delta_ensemble_names


# pylint: disable=too-many-instance-attributes
class SimulationTimeSeriesFilters(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        # NOTE: To force re-render of graph
        GRAPH_DATA_HAS_CHANGED_TRIGGER = "graph_data_has_changed_trigger"

        ENSEMBLES_DROPDOWN = "ensembles_dropdown"
        VECTOR_SELECTOR = "vector_selector"

        VECTOR_CALCULATOR = "vector_calculator"
        VECTOR_CALCULATOR_DIALOG = "vector_calculator_dialog"
        VECTOR_CALCULATOR_OPEN_BUTTON = "vector_calculator_open_button"
        VECTOR_CALCULATOR_EXPRESSIONS = "vector_calculator_expressions"
        VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG = (
            "vector_calculator_expressions_open_dialog"
        )

        DELTA_ENSEMBLE_A_DROPDOWN = "delta_ensemble_A_dropdown"
        DELTA_ENSEMBLE_B_DROPDOWN = "delta_ensemble_B_dropdown"
        DELTA_ENSEMBLE_CREATE_BUTTON = "delta_ensemble_create_button"
        CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "created_delta_ensemble_names_table"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
            "created_delta_ensemble_names_table_column"
        )

        RELATIVE_DATE_DROPDOWN = "relative_date_dropdown"

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

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def __init__(
        self,
        ensemble_names: List[str],
        vector_selector_data: list,
        vector_calculator_data: list,
        predefined_expressions: List[ExpressionInfo],
        custom_vector_definitions: dict,
        realizations: List[int],
        disable_resampling_dropdown: bool,
        selected_resampling_frequency: Frequency,
        selected_visualization: VisualizationOptions,
        ensembles_dates: List[datetime.datetime],
        get_data_output: Output,
        get_data_requested: Input,
        input_provider_set: ProviderSet,
        theme: WebvizConfigTheme,
        initial_selected_vectors: List[str],
        vector_selector_base_data: list,
        custom_vector_definitions_base: dict,
        observations: dict,  # TODO: Improve typehint?
        user_defined_vector_definitions: Dict[str, VectorDefinition],
        line_shape_fallback: str = "linear",
        selected_vectors: Optional[List[str]] = None,
    ) -> None:
        super().__init__("Data Filter")
        self.ensembles = ensemble_names
        self.vector_selector_data = vector_selector_data
        self.vector_calculator_data = vector_calculator_data
        self.predefined_expressions = predefined_expressions
        self.custom_vector_definitions = custom_vector_definitions
        self.realizations = realizations
        self.disable_resampling_dropdown = disable_resampling_dropdown
        self.selected_resampling_frequency = selected_resampling_frequency
        self.selected_visualization = selected_visualization
        self.ensembles_dates = ensembles_dates
        self.selected_vectors = selected_vectors

        self.get_data_output = get_data_output
        self.get_data_requested = get_data_requested
        self.input_provider_set = input_provider_set
        self.theme = theme
        self.initial_selected_vectors = initial_selected_vectors
        self.vector_selector_base_data = vector_selector_base_data
        self.custom_vector_definitions_base = custom_vector_definitions_base
        self.observations = observations
        self.user_defined_vector_definitions = user_defined_vector_definitions
        self.line_shape_fallback = line_shape_fallback

    def layout(self) -> List[Component]:
        return [
            wcc.Selectors(
                label="Group by",
                children=wcc.RadioItems(
                    id=self.register_component_unique_id(
                        self.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                    ),
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
            ),
            wcc.Selectors(
                label="Resampling frequency",
                children=[
                    wcc.Dropdown(
                        id=self.register_component_unique_id(
                            self.Ids.RESAMPLING_FREQUENCY_DROPDOWN
                        ),
                        clearable=False,
                        disabled=self.disable_resampling_dropdown,
                        options=[
                            {
                                "label": frequency.value,
                                "value": frequency.value,
                            }
                            for frequency in Frequency
                        ],
                        value=self.selected_resampling_frequency,
                        style={
                            "margin-bottom": "10px",
                        },
                    ),
                    wcc.Label(
                        "Data relative to date:",
                        style={
                            "font-style": "italic",
                        },
                    ),
                    wcc.Dropdown(
                        clearable=True,
                        disabled=self.disable_resampling_dropdown,
                        id=self.register_component_unique_id(
                            self.Ids.RELATIVE_DATE_DROPDOWN
                        ),
                        options=[
                            {
                                "label": datetime_utils.to_str(_date),
                                "value": datetime_utils.to_str(_date),
                            }
                            for _date in sorted(self.ensembles_dates)
                        ],
                    ),
                    wcc.Label(
                        "NB: Disabled for presampled data",
                        style={"font-style": "italic"}
                        if self.disable_resampling_dropdown
                        else {"display": "none"},
                    ),
                ],
            ),
            wcc.Selectors(
                label="Ensembles",
                children=[
                    wcc.Dropdown(
                        label="Selected ensembles",
                        id=self.register_component_unique_id(
                            self.Ids.ENSEMBLES_DROPDOWN
                        ),
                        clearable=False,
                        multi=True,
                        options=[
                            {"label": ensemble, "value": ensemble}
                            for ensemble in self.ensembles
                        ],
                        value=None if len(self.ensembles) <= 0 else [self.ensembles[0]],
                    ),
                    wcc.Selectors(
                        label="Delta Ensembles",
                        open_details=False,
                        children=[self.__delta_ensemble_creator_layout()],
                    ),
                ],
            ),
            wcc.Selectors(
                label="Time Series",
                children=[
                    wsc.VectorSelector(
                        id=self.register_component_unique_id(self.Ids.VECTOR_SELECTOR),
                        maxNumSelectedNodes=100,
                        data=self.vector_selector_data,
                        persistence=True,
                        persistence_type="session",
                        selectedTags=[]
                        if self.selected_vectors is None
                        else self.selected_vectors,
                        numSecondsUntilSuggestionsAreShown=0.5,
                        lineBreakAfterTag=True,
                        customVectorDefinitions=self.custom_vector_definitions,
                    ),
                    html.Button(
                        "Vector Calculator",
                        id=self.register_component_unique_id(
                            self.Ids.VECTOR_CALCULATOR_OPEN_BUTTON
                        ),
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
                        id=self.register_component_unique_id(
                            self.Ids.VISUALIZATION_RADIO_ITEMS
                        ),
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
                        value=self.selected_visualization.value,
                    ),
                    wcc.Selectors(
                        label="Options",
                        id=self.register_component_unique_id(
                            self.Ids.TOUR_STEP_OPTIONS
                        ),
                        children=self.__plot_options_layout(
                            selected_visualization=self.selected_visualization,
                        ),
                    ),
                ],
            ),
            wcc.Selectors(
                label="Filter Realizations",
                children=self.__realization_filters(self.realizations),
            ),
            self.__vector_calculator_dialog_layout(
                vector_data=self.vector_calculator_data,
                predefined_expressions=self.predefined_expressions,
            ),
            dcc.Store(
                id=self.register_component_unique_id(
                    self.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                ),
                data=self.predefined_expressions,
            ),
            dcc.Store(
                id=self.register_component_unique_id(
                    self.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                ),
                data=self.predefined_expressions,
            ),
            dcc.Store(
                # NOTE:Used to trigger graph update callback if data has
                # changed, i.e. no change of regular INPUT html-elements
                id=self.register_component_unique_id(
                    self.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ),
                data=0,
            ),
        ]

    def __vector_calculator_dialog_layout(
        self, vector_data: list, predefined_expressions: List[ExpressionInfo]
    ) -> wcc.Dialog:
        return wcc.Dialog(
            title="Vector Calculator",
            id=self.register_component_unique_id(self.Ids.VECTOR_CALCULATOR_DIALOG),
            draggable=True,
            max_width="lg",
            children=[
                html.Div(
                    style={"height": "60vh"},
                    children=[
                        wsc.VectorCalculator(
                            id=self.register_component_unique_id(
                                self.Ids.VECTOR_CALCULATOR
                            ),
                            vectors=vector_data,
                            expressions=predefined_expressions,
                        )
                    ],
                )
            ],
        )

    def __delta_ensemble_creator_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Dropdown(
                    label="Ensemble A",
                    id=self.register_component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_A_DROPDOWN
                    ),
                    clearable=False,
                    options=[{"label": i, "value": i} for i in self.ensembles],
                    value=self.ensembles[0],
                    style={"min-width": "60px"},
                ),
                wcc.Dropdown(
                    label="Ensemble B",
                    id=self.register_component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_B_DROPDOWN
                    ),
                    clearable=False,
                    options=[{"label": i, "value": i} for i in self.ensembles],
                    value=self.ensembles[-1],
                    style={"min-width": "60px"},
                ),
                html.Button(
                    "Create",
                    id=self.register_component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_CREATE_BUTTON
                    ),
                    n_clicks=0,
                    style={
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                        "min-width": "20px",
                    },
                ),
                self.__delta_ensemble_table_layout(),
                dcc.Store(
                    id=self.register_component_unique_id(
                        self.Ids.CREATED_DELTA_ENSEMBLES
                    ),
                    data=[],
                ),  # TODO: Add predefined deltas?
            ]
        )

    def __delta_ensemble_table_layout(self) -> dash_table.DataTable:
        return dash_table.DataTable(
            id=self.register_component_unique_id(
                self.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE
            ),
            columns=(
                [
                    {
                        "id": self.register_component_unique_id(
                            self.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
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

    def __realization_filters(self, realizations: List[int]) -> html.Div:
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
                            id=self.register_component_unique_id(
                                self.Ids.REALIZATIONS_FILTER_SPAN
                            ),
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
                    id=self.register_component_unique_id(
                        self.Ids.STATISTICS_FROM_RADIO_ITEMS
                    ),
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
                wcc.Select(
                    id=self.register_component_unique_id(
                        self.Ids.REALIZATIONS_FILTER_SELECTOR
                    ),
                    options=[{"label": i, "value": i} for i in realizations],
                    value=realizations,
                    size=min(10, len(realizations)),
                ),
            ],
        )

    def __plot_options_layout(
        self,
        selected_visualization: VisualizationOptions,
    ) -> html.Div:
        return html.Div(
            children=[
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"},
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
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                    ),
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
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                    ),
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

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.VECTOR_SELECTOR), "data"),
            Input(
                self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                "selectedNodes",
            ),
        )
        def update_store_vector_selector(selected_value: List[str]) -> List[str]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLES_DROPDOWN), "data"
            ),
            Input(
                self.component_unique_id(self.Ids.ENSEMBLES_DROPDOWN).to_string(),
                "value",
            ),
        )
        def update_store_ensemble_dropdown(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.CREATED_DELTA_ENSEMBLES).to_string(),
                "data",
            ),
        )
        def update_store_delta_ensemble(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.VISUALIZATION_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.VISUALIZATION_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def update_store_visualization_ratio(selected_value: List[str]) -> List[str]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def update_store_static_checklist(selected_value: List[str]) -> List[str]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_FANCHART_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def update_store_fanchart_checklist(selected_value: List[str]) -> List[str]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.PLOT_TRACE_OPTIONS_CHECKLIST),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def update_store_plot_checklist(selected_value: List[str]) -> List[str]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def update_store_subplot_items(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.RESAMPLING_FREQUENCY_DROPDOWN
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.RESAMPLING_FREQUENCY_DROPDOWN
                ).to_string(),
                "value",
            ),
        )
        def update_store_resampling_dropdown(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.REALIZATIONS_FILTER_SELECTOR),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def update_store_realization_selector(selected_value: List[int]) -> List[int]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.STATISTICS_FROM_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.STATISTICS_FROM_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def update_store_static_items(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.RELATIVE_DATE_DROPDOWN),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.RELATIVE_DATE_DROPDOWN).to_string(),
                "value",
            ),
        )
        def update_store_relative_dropdown(selected_value: str) -> str:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ).to_string(),
                "data",
            ),
        )
        def update_store_graph_trigger(selected_value: int) -> int:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.VECTOR_CALCULATOR_EXPRESSIONS
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                ).to_string(),
                "data",
            ),
        )
        def update_store_vector_calculator(
            selected_value: List[DeltaEnsemble],
        ) -> List[DeltaEnsemble]:
            return selected_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLES_DROPDOWN_OPTIONS),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.ENSEMBLES_DROPDOWN).to_string(),
                "options",
            ),
        )
        def update_store_ensemble_dropdown_options(
            selected_value: List[Dict],
        ) -> List[Dict]:
            return selected_value

        @callback(
            Output(
                self.component_unique_id(
                    self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Output(
                self.component_unique_id(
                    self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.VISUALIZATION_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def _update_statistics_options_layout(
            selected_visualization: str,
        ) -> List[dict]:
            """Only show statistics checklist if in statistics mode"""

            # Convert to enum type
            selected_visualization = VisualizationOptions(selected_visualization)

            def get_style(visualization_options: List[VisualizationOptions]) -> dict:
                return (
                    {"display": "block"}
                    if selected_visualization in visualization_options
                    else {"display": "none"}
                )

            statistics_options_style = get_style(
                [
                    VisualizationOptions.STATISTICS,
                    VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                ]
            )
            fanchart_options_style = get_style([VisualizationOptions.FANCHART])

            return [statistics_options_style, fanchart_options_style]

        @callback(
            [
                Output(
                    self.component_unique_id(
                        self.Ids.CREATED_DELTA_ENSEMBLES
                    ).to_string(),
                    "data",
                ),
                Output(
                    self.component_unique_id(
                        self.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE
                    ).to_string(),
                    "data",
                ),
                Output(
                    self.component_unique_id(self.Ids.ENSEMBLES_DROPDOWN).to_string(),
                    "options",
                ),
            ],
            [
                Input(
                    self.component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_CREATE_BUTTON
                    ).to_string(),
                    "n_clicks",
                )
            ],
            [
                State(
                    self.component_unique_id(self.Ids.ENSEMBLES_DROPDOWN).to_string(),
                    "options",
                ),
                State(
                    self.component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_A_DROPDOWN
                    ).to_string(),
                    "value",
                ),
                State(
                    self.component_unique_id(
                        self.Ids.DELTA_ENSEMBLE_B_DROPDOWN
                    ).to_string(),
                    "value",
                ),
            ],
        )
        def _update_created_delta_ensembles_names(
            n_clicks: int,
            existing_delta_ensembles: List[DeltaEnsemble],
            ensemble_a: str,
            ensemble_b: str,
        ) -> Tuple[List[DeltaEnsemble], List[Dict[str, str]], List[Dict[str, str]]]:

            if n_clicks is None or n_clicks < 0:
                raise PreventUpdate

            ensemble_options = [
                {"label": ensemble, "value": ensemble}
                for ensemble in self.input_provider_set.names()
            ]

            new_delta_ensembles: List = []
            table_data: List = []

            if n_clicks == 0:
                pass
            else:

                delta_ensemble = DeltaEnsemble(
                    ensemble_a=ensemble_a, ensemble_b=ensemble_b
                )

                if delta_ensemble in existing_delta_ensembles:
                    raise PreventUpdate

                # new_delta_ensembles = existing_delta_ensembles
                new_delta_ensembles = []
                new_delta_ensembles.append(delta_ensemble)

                # Create delta ensemble names
                new_delta_ensemble_names = create_delta_ensemble_names(
                    new_delta_ensembles
                )

                table_data = _create_delta_ensemble_table_column_data(
                    self.component_unique_id(
                        self.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
                    ).to_string(),
                    new_delta_ensemble_names,
                )

                for elm in new_delta_ensemble_names:
                    ensemble_options.append({"label": elm, "value": elm})

            return (new_delta_ensembles, table_data, ensemble_options)

        @callback(
            Output(
                self.component_unique_id(self.Ids.VECTOR_CALCULATOR_DIALOG).to_string(),
                "open",
            ),
            [
                Input(
                    self.component_unique_id(
                        self.Ids.VECTOR_CALCULATOR_OPEN_BUTTON
                    ).to_string(),
                    "n_clicks",
                ),
            ],
            [
                State(
                    self.component_unique_id(
                        self.Ids.VECTOR_CALCULATOR_DIALOG
                    ).to_string(),
                    "open",
                )
            ],
        )
        def _toggle_vector_calculator_dialog_open(
            n_open_clicks: int, is_open: bool
        ) -> bool:
            if n_open_clicks:
                return not is_open
            raise PreventUpdate

        @callback(
            Output(
                self.component_unique_id(self.Ids.VECTOR_CALCULATOR).to_string(),
                "externalParseData",
            ),
            Input(
                self.component_unique_id(self.Ids.VECTOR_CALCULATOR).to_string(),
                "externalParseExpression",
            ),
        )
        def _parse_vector_calculator_expression(
            expression: ExpressionInfo,
        ) -> ExternalParseData:
            if expression is None:
                raise PreventUpdate
            return wsc.VectorCalculator.external_parse_data(expression)

        @callback(
            [
                Output(
                    self.component_unique_id(
                        self.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                    ).to_string(),
                    "data",
                ),
                Output(
                    self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                    "data",
                ),
                Output(
                    self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                    "selectedTags",
                ),
                Output(
                    self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                    "customVectorDefinitions",
                ),
                Output(
                    self.component_unique_id(
                        self.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                    ).to_string(),
                    "data",
                ),
            ],
            Input(
                self.component_unique_id(self.Ids.VECTOR_CALCULATOR_DIALOG).to_string(),
                "open",
            ),
            [
                State(
                    self.component_unique_id(
                        self.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                    ).to_string(),
                    "data",
                ),
                State(
                    self.component_unique_id(
                        self.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                    ).to_string(),
                    "data",
                ),
                State(
                    self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                    "selectedNodes",
                ),
                State(
                    self.component_unique_id(self.Ids.VECTOR_SELECTOR).to_string(),
                    "customVectorDefinitions",
                ),
                State(
                    self.component_unique_id(
                        self.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                    ).to_string(),
                    "data",
                ),
            ],
        )
        def _update_vector_calculator_expressions_on_dialog_close(
            is_dialog_open: bool,
            new_expressions: List[ExpressionInfo],
            current_expressions: List[ExpressionInfo],
            current_selected_vectors: List[str],
            current_custom_vector_definitions: dict,
            graph_data_has_changed_counter: int,
        ) -> list:
            """Update vector calculator expressions, propagate expressions to VectorSelectors,
            update current selections and trigger re-rendering of graphing if necessary
            """
            # if callback_context.triggered[0]["prop_id"] == ".":
            #     current_expressions = self.predefined_expressions
            #     graph_data_has_changed_counter = 0
            # print("this is not the first time")

            if is_dialog_open or (new_expressions == current_expressions):
                raise PreventUpdate

            # Create current selected expressions for comparison - Deep copy!
            current_selected_expressions = get_selected_expressions(
                current_expressions, current_selected_vectors
            )

            # Create new vector selector data - Deep copy!
            new_vector_selector_data = copy.deepcopy(self.vector_selector_base_data)
            add_expressions_to_vector_selector_data(
                new_vector_selector_data, new_expressions
            )

            # Create new selected vectors - from new expressions
            new_selected_vectors = _create_new_selected_vectors(
                current_selected_vectors,
                current_expressions,
                new_expressions,
                new_vector_selector_data,
            )

            # Get new selected expressions
            new_selected_expressions = get_selected_expressions(
                new_expressions, new_selected_vectors
            )

            # Get new custom vector definitions
            new_custom_vector_definitions = get_vector_definitions_from_expressions(
                new_expressions
            )
            for key, value in self.custom_vector_definitions_base.items():
                if key not in new_custom_vector_definitions:
                    new_custom_vector_definitions[key] = value

            # Prevent updates if unchanged
            if new_custom_vector_definitions == current_custom_vector_definitions:
                new_custom_vector_definitions = dash.no_update

            if new_selected_vectors == current_selected_vectors:
                new_selected_vectors = dash.no_update

            # If selected expressions are edited
            # - Only trigger graph data update property when needed,
            # i.e. names are unchanged and selectedNodes for VectorSelector remains unchanged.
            new_graph_data_has_changed_counter = dash.no_update
            if (
                new_selected_expressions != current_selected_expressions
                and new_selected_vectors == dash.no_update
            ):
                new_graph_data_has_changed_counter = graph_data_has_changed_counter + 1

            return [
                new_expressions,
                new_vector_selector_data,
                new_selected_vectors,
                new_custom_vector_definitions,
                new_graph_data_has_changed_counter,
            ]

        @callback(
            Output(
                self.component_unique_id(
                    self.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                ).to_string(),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.VECTOR_CALCULATOR).to_string(),
                "expressions",
            ),
        )
        def _update_vector_calculator_expressions_when_dialog_open(
            expressions: List[ExpressionInfo],
        ) -> list:
            new_expressions: List[ExpressionInfo] = [
                elm for elm in expressions if elm["isValid"]
            ]
            return new_expressions

        @callback(
            Output(
                self.component_unique_id(self.Ids.REALIZATIONS_FILTER_SPAN).to_string(),
                "children",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _update_realization_range(realizations: List[int]) -> Optional[str]:
            if not realizations:
                raise PreventUpdate

            realizations_filter_text = printable_int_list(realizations)

            return realizations_filter_text

        @callback(
            [
                Output(
                    self.component_unique_id(
                        self.Ids.RELATIVE_DATE_DROPDOWN
                    ).to_string(),
                    "options",
                ),
                Output(
                    self.component_unique_id(
                        self.Ids.RELATIVE_DATE_DROPDOWN
                    ).to_string(),
                    "value",
                ),
            ],
            [
                Input(
                    self.component_unique_id(
                        self.Ids.RESAMPLING_FREQUENCY_DROPDOWN
                    ).to_string(),
                    "value",
                ),
            ],
            [
                State(
                    self.component_unique_id(
                        self.Ids.RELATIVE_DATE_DROPDOWN
                    ).to_string(),
                    "options",
                ),
                State(
                    self.component_unique_id(
                        self.Ids.RELATIVE_DATE_DROPDOWN
                    ).to_string(),
                    "value",
                ),
            ],
        )
        def _update_relative_date_dropdown(
            resampling_frequency_value: str,
            current_relative_date_options: List[dict],
            current_relative_date_value: Optional[str],
        ) -> Tuple[List[Dict[str, str]], Optional[str]]:
            """This callback updates dropdown based on selected resampling frequency selection

            If dates are not existing for a provider, the data accessor must handle invalid
            relative date selection!
            """
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )
            dates_union = self.input_provider_set.all_dates(resampling_frequency)

            # Create dropdown options:
            new_relative_date_options: List[Dict[str, str]] = [
                {
                    "label": datetime_utils.to_str(_date),
                    "value": datetime_utils.to_str(_date),
                }
                for _date in dates_union
            ]

            # Create valid dropdown value:
            new_relative_date_value = next(
                (
                    elm["value"]
                    for elm in new_relative_date_options
                    if elm["value"] == current_relative_date_value
                ),
                None,
            )

            # Prevent updates if unchanged
            if new_relative_date_options == current_relative_date_options:
                new_relative_date_options = dash.no_update
            if new_relative_date_value == current_relative_date_value:
                new_relative_date_value = dash.no_update

            return new_relative_date_options, new_relative_date_value

        @callback(
            [
                Output(
                    self.component_unique_id(
                        self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                    ).to_string(),
                    "style",
                ),
            ],
            [
                Input(
                    self.component_unique_id(
                        self.Ids.RELATIVE_DATE_DROPDOWN
                    ).to_string(),
                    "value",
                )
            ],
        )
        def _update_trace_options_layout(
            relative_date_value: str,
        ) -> List[dict]:
            """Hide trace options (History and Observation) when relative date is selected"""

            # Convert to Optional[datetime.datime]
            relative_date: Optional[datetime.datetime] = (
                None
                if relative_date_value is None
                else datetime_utils.from_str(relative_date_value)
            )

            if relative_date:
                return [{"display": "none"}]
            return [{"display": "block"}]

        @callback(
            Output(
                self.component_unique_id(
                    self.Ids.STATISTICS_FROM_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _update_realization_option(selected_value: List[int]) -> str:
            if len(selected_value) == len(self.realizations):
                return StatisticsFromOptions.ALL_REALIZATIONS.value
            return StatisticsFromOptions.SELECTED_REALIZATIONS.value


def _create_delta_ensemble_table_column_data(
    column_name: str, ensemble_names: List[str]
) -> List[Dict[str, str]]:
    return [{column_name: elm} for elm in ensemble_names]


def _create_new_selected_vectors(
    existing_selected_vectors: List[str],
    existing_expressions: List[ExpressionInfo],
    new_expressions: List[ExpressionInfo],
    new_vector_selector_data: list,
) -> List[str]:
    valid_selections: List[str] = []
    for vector in existing_selected_vectors:
        new_vector: Optional[str] = vector

        # Get id if vector is among existing expressions
        dropdown_id = next(
            (elm["id"] for elm in existing_expressions if elm["name"] == vector),
            None,
        )
        # Find id among new expressions to get new/edited name
        if dropdown_id:
            new_vector = next(
                (elm["name"] for elm in new_expressions if elm["id"] == dropdown_id),
                None,
            )

        # Append if vector name exist among data
        if new_vector is not None and is_vector_name_in_vector_selector_data(
            new_vector, new_vector_selector_data
        ):
            valid_selections.append(new_vector)
    return valid_selections
