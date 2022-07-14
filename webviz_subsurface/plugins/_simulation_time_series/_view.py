import datetime
from typing import Dict, List, Optional

import dash
import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config._theme_class import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_subsurface_components import ExpressionInfo, VectorDefinition

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.unique_theming import unique_colors
from webviz_subsurface._utils.vector_calculator import get_selected_expressions

from ._plugin_ids import PluginIds
from ._property_serialization import (
    EnsembleSubplotBuilder,
    GraphFigureBuilderBase,
    VectorSubplotBuilder,
)
from ._shared_settings import SimulationTimeSeriesFilters
from .types import (
    DeltaEnsemble,
    DerivedVectorsAccessor,
    FanchartOptions,
    ProviderSet,
    StatisticsFromOptions,
    StatisticsOptions,
    SubplotGroupByOptions,
    TraceOptions,
    VisualizationOptions,
)
from .utils import datetime_utils
from .utils.derived_ensemble_vectors_accessor_utils import (
    create_derived_vectors_accessor_dict,
)
from .utils.history_vectors import create_history_vectors_df
from .utils.provider_set_utils import create_vector_plot_titles_from_provider_set
from .utils.trace_line_shape import get_simulation_line_shape
from .utils.vector_statistics import create_vectors_statistics_df


class SimulationTimeSeriesView(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        CLOUMN = "column"
        GRAPH = "graph"

    def __init__(
        self,
        initial_selected_vectors: List[str],
        input_provider_set: ProviderSet,
        theme: WebvizConfigTheme,
        user_defined_vector_definitions: Dict[str, VectorDefinition],
        observations: dict,  # TODO: Improve typehint?
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__("")
        self.add_column(SimulationTimeSeriesView.Ids.GRAPH)
        self.initial_selected_vectors = initial_selected_vectors
        self.input_provider_set = input_provider_set
        self.theme = theme
        self.line_shape_fallback = line_shape_fallback
        self.user_defined_vector_definitions = user_defined_vector_definitions
        self.observations = observations

    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(SimulationTimeSeriesView.Ids.GRAPH)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.VECTOR_SELECTOR),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLES_DROPDOWN), "data"
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.VISUALIZATION_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_FANCHART_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.PLOT_TRACE_OPTIONS_CHECKLIST),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.RESAMPLING_FREQUENCY_DROPDOWN
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.REALIZATIONS_FILTER_SELECTOR),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.STATISTICS_FROM_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.RELATIVE_DATE_DROPDOWN),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ),
                "data",
            ),
            State(
                self.get_store_unique_id(PluginIds.Stores.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            State(
                self.get_store_unique_id(
                    PluginIds.Stores.VECTOR_CALCULATOR_EXPRESSIONS
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLES_DROPDOWN_OPTIONS),
                "data",
            ),
        )

        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        def _update_graph(
            vectors: List[str],
            selected_ensembles: List[str],
            visualization_value: str,
            statistics_option_values: List[str],
            fanchart_option_values: List[str],
            trace_option_values: List[str],
            subplot_owner_options_value: str,
            resampling_frequency_value: str,
            selected_realizations: List[int],
            statistics_calculated_from_value: str,
            relative_date_value: str,
            __graph_data_has_changed_trigger: int,
            delta_ensembles: List[DeltaEnsemble],
            vector_calculator_expressions: List[ExpressionInfo],
            ensemble_dropdown_options: List[dict],
        ) -> dict:
            """Callback to update all graphs based on selections

            * De-serialize from JSON serializable format to strongly typed and filtered format
            * Business logic:
                * Functionality with "strongly typed" and filtered input format - functions and
                classes
                * ProviderSet for EnsembleSummaryProviders, i.e. input_provider_set
                * DerivedEnsembleVectorsAccessor to access derived vector data from ensembles
                with single providers or delta ensemble with two providers
                * GraphFigureBuilder to create graph with subplots per vector or subplots per
                ensemble, using VectorSubplotBuilder and EnsembleSubplotBuilder, respectively
            * Create/build property serialization in FigureBuilder by use of business logic data

            NOTE: __graph_data_has_changed_trigger is only used to trigger callback when change of
            graphs data has changed and re-render of graph is necessary. E.g. when a selected
            expression from the VectorCalculator gets edited without changing the expression
            name - i.e.
            VectorSelector selectedNodes remain unchanged.
            """
            if not isinstance(selected_ensembles, list):
                raise TypeError("ensembles should always be of type list")

            if vectors is None:
                vectors = self.initial_selected_vectors
            # Retrieve the selected expressions
            selected_expressions = get_selected_expressions(
                vector_calculator_expressions, vectors
            )

            # Convert from string values to strongly typed
            visualization = VisualizationOptions(visualization_value)
            statistics_options = [
                StatisticsOptions(elm) for elm in statistics_option_values
            ]
            fanchart_options = [FanchartOptions(elm) for elm in fanchart_option_values]
            trace_options = [TraceOptions(elm) for elm in trace_option_values]
            subplot_owner = SubplotGroupByOptions(subplot_owner_options_value)
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )

            all_ensemble_names = [
                option["value"] for option in ensemble_dropdown_options
            ]
            statistics_from_option = StatisticsFromOptions(
                statistics_calculated_from_value
            )

            relative_date: Optional[datetime.datetime] = (
                None
                if relative_date_value is None
                else datetime_utils.from_str(relative_date_value)
            )

            # Prevent update if realization filtering is not affecting pure statistics plot
            # TODO: Refactor code or create utility for getting trigger ID in a "cleaner" way?
            ctx = dash.callback_context.triggered
            trigger_id = ctx[0]["prop_id"].split(".")[0]
            if (
                trigger_id
                == SimulationTimeSeriesFilters.component_unique_id(
                    self, SimulationTimeSeriesFilters.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string()
                and statistics_from_option is StatisticsFromOptions.ALL_REALIZATIONS
                and visualization
                in [
                    VisualizationOptions.STATISTICS,
                    VisualizationOptions.FANCHART,
                ]
            ):
                raise PreventUpdate

            # Create dict of derived vectors accessors for selected ensembles
            derived_vectors_accessors: Dict[
                str, DerivedVectorsAccessor
            ] = create_derived_vectors_accessor_dict(
                ensembles=selected_ensembles,
                vectors=vectors,
                provider_set=self.input_provider_set,
                expressions=selected_expressions,
                delta_ensembles=delta_ensembles,
                resampling_frequency=resampling_frequency,
                relative_date=relative_date,
            )

            # TODO: How to get metadata for calculated vector?
            vector_line_shapes: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    self.line_shape_fallback,
                    vector,
                    self.input_provider_set.vector_metadata(vector),
                )
                for vector in vectors
            }

            figure_builder: GraphFigureBuilderBase
            if subplot_owner is SubplotGroupByOptions.VECTOR:
                # Create unique colors based on all ensemble names to preserve consistent colors
                ensemble_colors = unique_colors(all_ensemble_names, self.theme)
                vector_titles = create_vector_plot_titles_from_provider_set(
                    vectors,
                    selected_expressions,
                    self.input_provider_set,
                    self.user_defined_vector_definitions,
                    resampling_frequency,
                )
                figure_builder = VectorSubplotBuilder(
                    vectors,
                    vector_titles,
                    ensemble_colors,
                    resampling_frequency,
                    vector_line_shapes,
                    self.theme,
                )
            elif subplot_owner is SubplotGroupByOptions.ENSEMBLE:
                vector_colors = unique_colors(vectors, self.theme)
                figure_builder = EnsembleSubplotBuilder(
                    vectors,
                    selected_ensembles,
                    vector_colors,
                    resampling_frequency,
                    vector_line_shapes,
                    self.theme,
                )
            else:
                raise PreventUpdate

            # Get all realizations if statistics accross all realizations are requested
            is_statistics_from_all_realizations = (
                statistics_from_option == StatisticsFromOptions.ALL_REALIZATIONS
                and visualization
                in [
                    VisualizationOptions.FANCHART,
                    VisualizationOptions.STATISTICS,
                    VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                ]
            )

            # Plotting per derived vectors accessor
            for ensemble, accessor in derived_vectors_accessors.items():
                # Realization query - realizations query for accessor
                # - Get non-filter query, None, if statistics from all realizations is needed
                # - Create valid realizations query for accessor otherwise:
                #   * List[int]: Filtered valid realizations, empty list if none are valid
                #   * None: Get all realizations, i.e. non-filtered query
                realizations_query = (
                    None
                    if is_statistics_from_all_realizations
                    else accessor.create_valid_realizations_query(selected_realizations)
                )

                # If all selected realizations are invalid for accessor - empty list
                if realizations_query == []:
                    continue

                # TODO: Consider to remove list vectors_df_list and use pd.concat to obtain
                # one single dataframe with vector columns. NB: Assumes equal sampling rate
                # for each vector type - i.e equal number of rows in dataframes

                # Retrive vectors data from accessor
                vectors_df_list: List[pd.DataFrame] = []
                if accessor.has_provider_vectors():
                    vectors_df_list.append(
                        accessor.get_provider_vectors_df(
                            realizations=realizations_query
                        )
                    )
                if accessor.has_per_interval_and_per_day_vectors():
                    vectors_df_list.append(
                        accessor.create_per_interval_and_per_day_vectors_df(
                            realizations=realizations_query
                        )
                    )
                if accessor.has_vector_calculator_expressions():
                    vectors_df_list.append(
                        accessor.create_calculated_vectors_df(
                            realizations=realizations_query
                        )
                    )

                for vectors_df in vectors_df_list:
                    # Ensure rows of data
                    if not vectors_df.shape[0]:
                        continue

                    if visualization == VisualizationOptions.REALIZATIONS:
                        # Show selected realizations - only filter df if realizations filter
                        # query is not performed
                        figure_builder.add_realizations_traces(
                            vectors_df
                            if realizations_query
                            else vectors_df[
                                vectors_df["REAL"].isin(selected_realizations)
                            ],
                            ensemble,
                        )
                    if visualization == VisualizationOptions.STATISTICS:
                        vectors_statistics_df = create_vectors_statistics_df(vectors_df)
                        figure_builder.add_statistics_traces(
                            vectors_statistics_df,
                            ensemble,
                            statistics_options,
                        )
                    if visualization == VisualizationOptions.FANCHART:
                        vectors_statistics_df = create_vectors_statistics_df(vectors_df)
                        figure_builder.add_fanchart_traces(
                            vectors_statistics_df,
                            ensemble,
                            fanchart_options,
                        )
                    if (
                        visualization
                        == VisualizationOptions.STATISTICS_AND_REALIZATIONS
                    ):
                        # Configure line width and color scaling to easier separate
                        # statistics traces and realization traces.
                        # Show selected realizations - only filter df if realizations filter
                        # query is not performed
                        figure_builder.add_realizations_traces(
                            vectors_df
                            if realizations_query
                            else vectors_df[
                                vectors_df["REAL"].isin(selected_realizations)
                            ],
                            ensemble,
                            color_lightness_scale=150.0,
                        )
                        # Add statistics on top
                        vectors_statistics_df = create_vectors_statistics_df(vectors_df)
                        figure_builder.add_statistics_traces(
                            vectors_statistics_df,
                            ensemble,
                            statistics_options,
                            line_width=3,
                        )

            # Retrieve selected input providers
            selected_input_providers = ProviderSet(
                {
                    name: provider
                    for name, provider in self.input_provider_set.items()
                    if name in selected_ensembles
                }
            )

            # Do not add observations if only delta ensembles are selected
            is_only_delta_ensembles = (
                len(selected_input_providers.names()) == 0
                and len(derived_vectors_accessors) > 0
            )
            if (
                self.observations
                and TraceOptions.OBSERVATIONS in trace_options
                and not is_only_delta_ensembles
                and not relative_date
            ):
                for vector in vectors:
                    vector_observations = self.observations.get(vector)
                    if vector_observations:
                        figure_builder.add_vector_observations(
                            vector, vector_observations
                        )

            # Add history trace
            # TODO: Improve when new history vector input format is in place
            if TraceOptions.HISTORY in trace_options and not relative_date:
                if (
                    isinstance(figure_builder, VectorSubplotBuilder)
                    and len(selected_input_providers.names()) > 0
                ):
                    # Add history trace using first selected ensemble
                    name = selected_input_providers.names()[0]
                    provider = selected_input_providers.provider(name)
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
                            figure_builder.add_history_traces(history_vectors_df)

                if isinstance(figure_builder, EnsembleSubplotBuilder):
                    # Add history trace for each ensemble
                    for name, provider in selected_input_providers.items():
                        vector_names = provider.vector_names()

                        provider_vectors = [
                            elm for elm in vectors if elm in vector_names
                        ]
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
                                    history_vectors_df,
                                    name,
                                )

            # Create legends when all data is added to figure
            figure_builder.create_graph_legends()

            return (
                wcc.Graph(
                    style={"height": "85vh"},
                    id="time-series-graph",
                    figure=figure_builder.get_serialized_figure(),
                ),
            )
