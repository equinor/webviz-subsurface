from typing import Callable, Dict, List, Optional, Tuple

import copy
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import pandas as pd

import webviz_subsurface_components as wsc
from webviz_subsurface_components import ExpressionInfo, ExternalParseData
from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.unique_theming import unique_colors


from ._layout import LayoutElements
from ._property_serialization import GraphFigureBuilder

from .types import (
    AssortedVectorDataAccessor,
    create_delta_ensemble_names,
    DeltaEnsembleNamePair,
    DeltaEnsembleProvider,
    FanchartOptions,
    StatisticsOptions,
    ProviderSet,
    TraceOptions,
    VisualizationOptions,
)
from .utils.trace_line_shape import get_simulation_line_shape
from .utils.provider_set_utils import (
    create_selected_provider_set,
    create_vector_plot_titles_from_provider_set,
)
from .utils.vector_statistics import create_vectors_statistics_df
from .utils.history_vectors import create_history_vectors_df

from ..._utils.vector_calculator import (
    add_expressions_to_vector_selector_data,
    get_custom_vector_definitions_from_expressions,
    get_selected_expressions,
)
from ..._utils.vector_selector import is_vector_name_in_vector_selector_data

# TODO: Consider adding: presampled_frequency: Optional[Frequency] argument for use when
# providers are presampled. To keep track of sampling frequency, and not depend on dropdown
# value for ViewElements.RESAMPLING_FREQUENCY_DROPDOWN (dropdown disabled when providers are
# presampled)
# pylint: disable = too-many-arguments, too-many-branches, too-many-locals, too-many-statements
def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    input_provider_set: ProviderSet,
    theme: WebvizConfigTheme,
    initial_selected_vectors: List[str],
    vector_selector_base_data: list,
    observations: dict,  # TODO: Improve typehint?
    line_shape_fallback: str = "linear",
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.GRAPH), "figure"),
        [
            Input(
                get_uuid(LayoutElements.VECTOR_SELECTOR),
                "selectedNodes",
            ),
            Input(get_uuid(LayoutElements.ENSEMBLES_DROPDOWN), "value"),
            Input(
                get_uuid(LayoutElements.VISUALIZATION_RADIO_ITEMS),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.GRAPH_DATA_HAS_CHANGED_TRIGGER),
                "data",
            ),
        ],
        [
            State(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            State(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS),
                "data",
            ),
        ],
    )
    def _update_graph(
        vectors: List[str],
        selected_ensembles: List[str],
        visualization_value: str,
        statistics_option_values: List[str],
        fanchart_option_values: List[str],
        trace_option_values: List[str],
        resampling_frequency_value: str,
        __graph_data_has_changed_trigger: int,
        delta_ensembles: List[DeltaEnsembleNamePair],
        vector_calculator_expressions: List[ExpressionInfo],
    ) -> dict:
        """Callback to update all graphs based on selections

        * De-serialize from JSON serializable format to strongly typed and filtered format
        * Business logic with SelectedProviderSet, ProviderVectorDataHandler and utility functions
        with "strongly typed" and filtered input format
        * Create/build prop serialization in FigureBuilder by use of business logic data

        NOTE: __graph_data_has_changed_trigger is only used to trigger callback when change of
        graphs data has changed and re-render of graph is necessary. E.g. when a selected expression
        from the VectorCalculatorgets edited, without changing the expression name - i.e.
        VectorSelector selectedNodes remain unchanged.
        """
        if vectors is None:
            vectors = initial_selected_vectors

        # Retrieve the selected expressions
        selected_expressions = get_selected_expressions(
            vector_calculator_expressions, vectors
        )

        # Convert from string values to enum types
        visualization = VisualizationOptions(visualization_value)
        statistics_options = [
            StatisticsOptions(elm) for elm in statistics_option_values
        ]
        fanchart_options = [FanchartOptions(elm) for elm in fanchart_option_values]
        trace_options = [TraceOptions(elm) for elm in trace_option_values]
        resampling_frequency = Frequency.from_string_value(resampling_frequency_value)

        if not isinstance(selected_ensembles, list):
            raise TypeError("ensembles should always be of type list")

        # Filter selected delta ensembles
        selected_provider_set = create_selected_provider_set(
            input_provider_set, selected_ensembles, delta_ensembles
        )

        # Titles for subplots
        vector_titles = create_vector_plot_titles_from_provider_set(
            vectors, selected_expressions, selected_provider_set
        )

        # TODO: Create unique colors based on all ensembles, i.e. union of
        # ensemble_set_model.ensemble_names() and create_delta_ensemble_names(delta_ensembles)
        # Now color can change when changing selected ensembles?
        ensemble_colors = unique_colors(selected_provider_set.names(), theme)

        # TODO: Pass presampling_frequency when using presampled providers?
        # NOTE: Dropdown value is equal to presampling_frequency when presampled providers
        # are utilized.
        figure_builder = GraphFigureBuilder(
            vectors, vector_titles, ensemble_colors, resampling_frequency, theme
        )

        # TODO: How to handle vector metadata the best way?
        vector_line_shapes: Dict[str, str] = {
            vector: get_simulation_line_shape(
                line_shape_fallback,
                vector,
                selected_provider_set.vector_metadata(vector),
            )
            for vector in vectors
        }

        # Plotting per ensemble
        for name, provider in selected_provider_set.items():
            vector_data_accessor = AssortedVectorDataAccessor(
                name,
                provider,
                vectors,
                expressions=selected_expressions,
                resampling_frequency=resampling_frequency
                if provider.supports_resampling()
                else None,
            )

            vectors_df_list: List[pd.DataFrame] = []
            if vector_data_accessor.has_provider_vectors():
                vectors_df_list.append(vector_data_accessor.get_provider_vectors_df())
            if vector_data_accessor.has_interval_and_average_vectors():
                vectors_df_list.append(
                    vector_data_accessor.create_interval_and_average_vectors_df()
                )
            if vector_data_accessor.has_vector_calculator_expressions():
                vectors_df_list.append(
                    vector_data_accessor.create_calculated_vectors_df()
                )

            for index, vectors_df in enumerate(vectors_df_list):
                if visualization == VisualizationOptions.REALIZATIONS:
                    figure_builder.add_realizations_traces(
                        vectors_df,
                        name,
                        vector_line_shapes,
                        add_legend=index == 0,
                    )
                if visualization == VisualizationOptions.STATISTICS:
                    vectors_statistics_df = create_vectors_statistics_df(vectors_df)
                    figure_builder.add_statistics_traces(
                        vectors_statistics_df,
                        name,
                        statistics_options,
                        vector_line_shapes,
                        add_legend=index == 0,
                    )
                if visualization == VisualizationOptions.FANCHART:
                    vectors_statistics_df = create_vectors_statistics_df(vectors_df)
                    figure_builder.add_fanchart_traces(
                        vectors_statistics_df,
                        name,
                        fanchart_options,
                        vector_line_shapes,
                        add_legend=index == 0,
                    )

        # Do not add observations if only delta ensembles are selected
        is_only_delta_ensembles = all(
            isinstance(elm, DeltaEnsembleProvider)
            for elm in selected_provider_set.all_providers()
        )
        if observations and not is_only_delta_ensembles:
            for vector in vectors:
                vector_observations = observations.get(vector)
                if vector_observations:
                    figure_builder.add_vector_observations(vector, vector_observations)

        if (
            TraceOptions.HISTORY in trace_options
            and len(selected_provider_set.names()) > 0
        ):
            # NOTE: Retrieve historical vector from first ensemble
            # Name and provider from first selected ensemble
            name = selected_provider_set.names()[0]
            provider = selected_provider_set.provider(name)
            vector_names = provider.vector_names()

            provider_vectors = [elm for elm in vectors if elm in vector_names]

            if provider_vectors:
                history_vectors_df = create_history_vectors_df(
                    provider, provider_vectors, resampling_frequency
                )
                # TODO: Handle check of non-empty dataframe better?
                if (
                    not history_vectors_df.empty
                    and "DATE" in history_vectors_df.columns
                ):
                    figure_builder.add_history_traces(
                        history_vectors_df, vector_line_shapes
                    )

        return figure_builder.get_serialized_figure()

    # TODO: Implement callback
    # @app.callback()
    # def _user_download_data() -> None:
    #     raise NotImplementedError()

    @app.callback(
        [
            Output(
                get_uuid(LayoutElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                "style",
            ),
            Output(
                get_uuid(LayoutElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
                "style",
            ),
        ],
        [
            Input(
                get_uuid(LayoutElements.VISUALIZATION_RADIO_ITEMS),
                "value",
            )
        ],
    )
    def _update_statistics_options_layout(visualization: str) -> List[dict]:
        """Only show statistics checklist if in statistics mode"""

        # Convert to enum type
        visualization = VisualizationOptions(visualization)

        def get_style(visualization_type: VisualizationOptions) -> dict:
            return (
                {"display": "block"}
                if visualization == visualization_type
                else {"display": "none"}
            )

        statistics_options_style = get_style(VisualizationOptions.STATISTICS)
        fanchart_options_style = get_style(VisualizationOptions.FANCHART)

        return [statistics_options_style, fanchart_options_style]

    @app.callback(
        [
            Output(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            Output(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE),
                "data",
            ),
            Output(
                get_uuid(LayoutElements.ENSEMBLES_DROPDOWN),
                "options",
            ),
        ],
        [
            Input(
                get_uuid(LayoutElements.DELTA_ENSEMBLE_CREATE_BUTTON),
                "n_clicks",
            )
        ],
        [
            State(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            State(
                get_uuid(LayoutElements.DELTA_ENSEMBLE_A_DROPDOWN),
                "value",
            ),
            State(
                get_uuid(LayoutElements.DELTA_ENSEMBLE_B_DROPDOWN),
                "value",
            ),
        ],
    )
    def _update_created_delta_ensembles_names(
        n_clicks: int,
        existing_delta_ensembles: List[DeltaEnsembleNamePair],
        ensemble_a: str,
        ensemble_b: str,
    ) -> Tuple[List[DeltaEnsembleNamePair], List[Dict[str, str]], List[Dict[str, str]]]:
        if n_clicks is None or n_clicks <= 0:
            raise PreventUpdate

        delta_ensemble = DeltaEnsembleNamePair(
            ensemble_a=ensemble_a, ensemble_b=ensemble_b
        )
        if delta_ensemble in existing_delta_ensembles:
            raise PreventUpdate

        new_delta_ensembles = existing_delta_ensembles
        new_delta_ensembles.append(delta_ensemble)

        # Create delta ensemble names
        new_delta_ensemble_names = create_delta_ensemble_names(new_delta_ensembles)

        table_data = _create_delta_ensemble_table_column_data(
            get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN),
            new_delta_ensemble_names,
        )

        ensemble_options = [
            {"label": ensemble, "value": ensemble}
            for ensemble in input_provider_set.names()
        ]
        for elm in new_delta_ensemble_names:
            ensemble_options.append({"label": elm, "value": elm})

        return (new_delta_ensembles, table_data, ensemble_options)

    @app.callback(
        Output(get_uuid(LayoutElements.VECTOR_CALCULATOR_MODAL), "is_open"),
        [
            Input(get_uuid(LayoutElements.VECTOR_CALCULATOR_OPEN_BUTTON), "n_clicks"),
        ],
        [State(get_uuid(LayoutElements.VECTOR_CALCULATOR_MODAL), "is_open")],
    )
    def _toggle_vector_calculator_modal(n_open_clicks: int, is_open: bool) -> bool:
        if n_open_clicks:
            return not is_open
        raise PreventUpdate

    @app.callback(
        Output(get_uuid(LayoutElements.VECTOR_CALCULATOR), "externalParseData"),
        Input(get_uuid(LayoutElements.VECTOR_CALCULATOR), "externalParseExpression"),
    )
    def _parse_vector_calculator_expression(
        expression: ExpressionInfo,
    ) -> ExternalParseData:
        if expression is None:
            raise PreventUpdate
        return wsc.VectorCalculator.external_parse_data(expression)

    @app.callback(
        [
            Output(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS),
                "data",
            ),
            Output(get_uuid(LayoutElements.VECTOR_SELECTOR), "data"),
            Output(get_uuid(LayoutElements.VECTOR_SELECTOR), "selectedTags"),
            Output(get_uuid(LayoutElements.VECTOR_SELECTOR), "customVectorDefinitions"),
            Output(
                get_uuid(LayoutElements.GRAPH_DATA_HAS_CHANGED_TRIGGER),
                "data",
            ),
        ],
        Input(get_uuid(LayoutElements.VECTOR_CALCULATOR_MODAL), "is_open"),
        [
            State(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_MODAL),
                "data",
            ),
            State(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS),
                "data",
            ),
            State(get_uuid(LayoutElements.VECTOR_SELECTOR), "selectedNodes"),
            State(get_uuid(LayoutElements.VECTOR_SELECTOR), "customVectorDefinitions"),
            State(
                get_uuid(LayoutElements.GRAPH_DATA_HAS_CHANGED_TRIGGER),
                "data",
            ),
        ],
    )
    def _update_vector_calculator_expressions_on_modal_close(
        is_modal_open: bool,
        new_expressions: List[ExpressionInfo],
        current_expressions: List[ExpressionInfo],
        current_selected_vectors: List[str],
        current_custom_vector_definitions: dict,
        graph_data_has_changed_counter: int,
    ) -> list:
        """Update vector calculator expressions, propagate expressions to VectorSelectors,
        update current selections and trigger re-rendering of graphing if necessary
        """
        if is_modal_open or (new_expressions == current_expressions):
            raise PreventUpdate

        # Create current selected expressions for comparison - Deep copy!
        current_selected_expressions = get_selected_expressions(
            current_expressions, current_selected_vectors
        )

        # Create new vector selector data - Deep copy!
        new_vector_selector_data = copy.deepcopy(vector_selector_base_data)
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
        new_custom_vector_definitions = get_custom_vector_definitions_from_expressions(
            new_expressions
        )

        # Prevent updates if unchanged
        if new_custom_vector_definitions == current_custom_vector_definitions:
            new_custom_vector_definitions = dash.no_update

        if new_selected_vectors == current_selected_vectors:
            new_selected_vectors = dash.no_update

        # If selected expressions are edited - Only trigger graph data update property when needed,
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

    @app.callback(
        Output(
            get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_MODAL),
            "data",
        ),
        Input(get_uuid(LayoutElements.VECTOR_CALCULATOR), "expressions"),
    )
    def _update_vector_calculator_expressions_when_modal_open(
        expressions: List[ExpressionInfo],
    ) -> list:
        new_expressions: List[ExpressionInfo] = [
            elm for elm in expressions if elm["isValid"]
        ]
        return new_expressions


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
