import datetime
from typing import Dict, List, Optional, Tuple, Union

import dash
import pandas as pd
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile, WebvizPluginABC
from webviz_config._theme_class import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_subsurface_components import ExpressionInfo, VectorDefinition

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)
from webviz_subsurface._utils.unique_theming import unique_colors
from webviz_subsurface._utils.vector_calculator import get_selected_expressions

from ._property_serialization import (
    EnsembleSubplotBuilder,
    GraphFigureBuilderBase,
    VectorSubplotBuilder,
)
from ._settings._ensembles import EnsemblesSettings
from ._settings._filter_realization import FilterRealizationSettings
from ._settings._group_by import GroupBySettings
from ._settings._resampling_frequency import ResamplingFrequencySettings
from ._settings._time_series import TimeSeriesSettings
from ._settings._visualization import VisualizationSettings
from ._types import (
    DeltaEnsemble,
    FanchartOptions,
    StatisticsFromOptions,
    StatisticsOptions,
    SubplotGroupByOptions,
    TraceOptions,
    VisualizationOptions,
)
from ._utils import DerivedVectorsAccessor, datetime_utils
from ._utils.derived_ensemble_vectors_accessor_utils import (
    create_derived_vectors_accessor_dict,
)
from ._utils.ensemble_summary_provider_set_utils import (
    create_vector_plot_titles_from_provider_set,
)
from ._utils.from_timeseries_cumulatives import (
    datetime_to_intervalstr,
    is_per_interval_or_per_day_vector,
)
from ._utils.history_vectors import create_history_vectors_df
from ._utils.trace_line_shape import get_simulation_line_shape
from ._utils.vector_statistics import create_vectors_statistics_df
from ._view_elements import SubplotGraph


class SubplotView(ViewABC):
    class Ids(StrEnum):
        SUBPLOT = "subplot"

        ENSEMBLE_SETTINGS = "ensemble-settings"
        FILTER_REALIZATION_SETTINGS = "filter-realization-settings"
        GROUP_BY_SETTINGS = "group-by-settings"
        RESAMPLING_FREQUENCY_SETTINGS = "resampling-frequency-settings"
        TIME_SERIES_SETTINGS = "time-series-settings"
        VISUALIZATION_SETTINGS = "visualization-settings"

    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        custom_vector_definitions: dict,
        custom_vector_definitions_base: dict,
        disable_resampling_dropdown: bool,
        initial_selected_vectors: List[str],
        initial_vector_selector_data: list,
        initial_visualization: VisualizationOptions,
        input_provider_set: EnsembleSummaryProviderSet,
        predefined_expressions: List[ExpressionInfo],
        selected_resampling_frequency: Frequency,
        vector_calculator_data: List,
        vector_selector_base_data: list,
        theme: WebvizConfigTheme,
        user_defined_vector_definitions: Dict[str, VectorDefinition],
        observations: dict,  # TODO: Improve typehint?
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__("Subplot View")

        column = self.add_column()
        column.add_view_element(SubplotGraph(), SubplotView.Ids.SUBPLOT)

        self.add_settings_groups(
            {
                SubplotView.Ids.GROUP_BY_SETTINGS: GroupBySettings(),
                SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS: ResamplingFrequencySettings(
                    disable_resampling_dropdown=disable_resampling_dropdown,
                    selected_resampling_frequency=selected_resampling_frequency,
                    ensembles_dates=input_provider_set.all_dates(
                        selected_resampling_frequency
                    ),
                    input_provider_set=input_provider_set,
                ),
                SubplotView.Ids.ENSEMBLE_SETTINGS: EnsemblesSettings(
                    ensembles_names=input_provider_set.provider_names(),
                    input_provider_set=input_provider_set,
                ),
                SubplotView.Ids.TIME_SERIES_SETTINGS: TimeSeriesSettings(
                    initial_vector_selector_data=initial_vector_selector_data,
                    custom_vector_definitions=custom_vector_definitions,
                    vector_calculator_data=vector_calculator_data,
                    predefined_expressions=predefined_expressions,
                    vector_selector_base_data=vector_selector_base_data,
                    custom_vector_definitions_base=custom_vector_definitions_base,
                    initial_selected_vectors=initial_selected_vectors,
                ),
                SubplotView.Ids.VISUALIZATION_SETTINGS: VisualizationSettings(
                    selected_visualization=initial_visualization
                ),
                SubplotView.Ids.FILTER_REALIZATION_SETTINGS: FilterRealizationSettings(
                    realizations=input_provider_set.all_realizations()
                ),
            }
        )

        self._initial_selected_vectors = initial_selected_vectors
        self._input_provider_set = input_provider_set
        self._theme = theme
        self._line_shape_fallback = line_shape_fallback
        self._user_defined_vector_definitions = user_defined_vector_definitions
        self._observations = observations

    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element_unique_id(
                    SubplotView.Ids.SUBPLOT, SubplotGraph.Ids.GRAPH
                ),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.TIME_SERIES_SETTINGS,
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR,
                ),
                "selectedNodes",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.ENSEMBLE_SETTINGS,
                    EnsemblesSettings.Ids.ENSEMBLES_DROPDOWN,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.VISUALIZATION_RADIO_ITEMS,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.PLOT_TRACE_OPTIONS_CHECKLIST,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.GROUP_BY_SETTINGS,
                    GroupBySettings.Ids.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RESAMPLING_FREQUENCY_DROPDOWN,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.FILTER_REALIZATION_SETTINGS,
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SELECTOR,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.FILTER_REALIZATION_SETTINGS,
                    FilterRealizationSettings.Ids.STATISTICS_FROM_RADIO_ITEMS,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.TIME_SERIES_SETTINGS,
                    TimeSeriesSettings.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER,
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.ENSEMBLE_SETTINGS,
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLES_STORE,
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.TIME_SERIES_SETTINGS,
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS,
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.ENSEMBLE_SETTINGS,
                    EnsemblesSettings.Ids.ENSEMBLES_DROPDOWN,
                ),
                "options",
            ),
        )
        @callback_typecheck
        # pylint: disable=too-many-arguments, too-many-locals, too-many-branches, too-many-statements
        def _update_graph(
            vectors: List[str],
            selected_ensembles: List[str],
            visualization: VisualizationOptions,
            statistics_options: List[StatisticsOptions],
            fanchart_options: List[FanchartOptions],
            trace_options: List[TraceOptions],
            subplot_group_by: SubplotGroupByOptions,
            resampling_frequency_value: str,
            selected_realizations: List[int],
            statistics_from: StatisticsFromOptions,
            relative_date_value: Optional[str],
            _graph_data_has_changed_trigger: int,
            delta_ensembles: List[DeltaEnsemble],
            vector_calculator_expressions: List[ExpressionInfo],
            ensemble_dropdown_options: List[dict],
        ) -> dict:
            """Callback to update all graphs based on selections

            * De-serialize from JSON serializable format to strongly typed and filtered format
            * Business logic:
                * Functionality with "strongly typed" and filtered input format - functions and
                classes
                * EnsembleSummaryProviderSet for EnsembleSummaryProviders, i.e. input_provider_set
                * DerivedEnsembleVectorsAccessor to access derived vector data from ensembles
                with single providers or delta ensemble with two providers
                * GraphFigureBuilder to create graph with subplots per vector or subplots per
                ensemble, using VectorSubplotBuilder and EnsembleSubplotBuilder, respectively
            * Create/build property serialization in FigureBuilder by use of business logic data

            NOTE: _graph_data_has_changed_trigger is only used to trigger callback when change of
            graphs data has changed and re-render of graph is necessary. E.g. when a selected
            expression from the VectorCalculator gets edited without changing the expression
            name - i.e.
            VectorSelector selectedNodes remain unchanged.
            """
            if not isinstance(selected_ensembles, list):
                raise TypeError("ensembles should always be of type list")

            if vectors is None:
                vectors = self._initial_selected_vectors

            # Retrieve the selected expressions
            selected_expressions = get_selected_expressions(
                vector_calculator_expressions, vectors
            )

            # Convert from string values to strongly typed
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )

            all_ensemble_names = [
                option["value"] for option in ensemble_dropdown_options
            ]

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
                == self.settings_group_unique_id(
                    SubplotView.Ids.FILTER_REALIZATION_SETTINGS,
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SELECTOR,
                )
                and statistics_from is StatisticsFromOptions.ALL_REALIZATIONS
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
                provider_set=self._input_provider_set,
                expressions=selected_expressions,
                delta_ensembles=delta_ensembles,
                resampling_frequency=resampling_frequency,
                relative_date=relative_date,
            )

            # TODO: How to get metadata for calculated vector?
            vector_line_shapes: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    self._line_shape_fallback,
                    vector,
                    self._input_provider_set.vector_metadata(vector),
                )
                for vector in vectors
            }

            figure_builder: GraphFigureBuilderBase
            if subplot_group_by is SubplotGroupByOptions.VECTOR:
                # Create unique colors based on all ensemble names to preserve consistent colors
                ensemble_colors = unique_colors(all_ensemble_names, self._theme)
                vector_titles = create_vector_plot_titles_from_provider_set(
                    vectors,
                    selected_expressions,
                    self._input_provider_set,
                    self._user_defined_vector_definitions,
                    resampling_frequency,
                )
                figure_builder = VectorSubplotBuilder(
                    vectors,
                    vector_titles,
                    ensemble_colors,
                    resampling_frequency,
                    vector_line_shapes,
                    self._theme,
                )
            elif subplot_group_by is SubplotGroupByOptions.ENSEMBLE:
                vector_colors = unique_colors(vectors, self._theme)
                figure_builder = EnsembleSubplotBuilder(
                    vectors,
                    selected_ensembles,
                    vector_colors,
                    resampling_frequency,
                    vector_line_shapes,
                    self._theme,
                )
            else:
                raise PreventUpdate

            # Get all realizations if statistics accross all realizations are requested
            is_statistics_from_all_realizations = (
                statistics_from == StatisticsFromOptions.ALL_REALIZATIONS
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
            selected_input_providers = EnsembleSummaryProviderSet(
                {
                    name: provider
                    for name, provider in self._input_provider_set.items()
                    if name in selected_ensembles
                }
            )

            # Do not add observations if only delta ensembles are selected
            is_only_delta_ensembles = (
                len(selected_input_providers.provider_names()) == 0
                and len(derived_vectors_accessors) > 0
            )
            if (
                self._observations
                and TraceOptions.OBSERVATIONS in trace_options
                and not is_only_delta_ensembles
                and not relative_date
            ):
                for vector in vectors:
                    vector_observations = self._observations.get(vector)
                    if vector_observations:
                        figure_builder.add_vector_observations(
                            vector, vector_observations
                        )

            # Add history trace
            # TODO: Improve when new history vector input format is in place
            if TraceOptions.HISTORY in trace_options and not relative_date:
                if (
                    isinstance(figure_builder, VectorSubplotBuilder)
                    and len(selected_input_providers.provider_names()) > 0
                ):
                    # Add history trace using first selected ensemble
                    name = selected_input_providers.provider_names()[0]
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

            return figure_builder.get_serialized_figure()

        @callback(
            self.view_data_output(),
            self.view_data_requested(),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.TIME_SERIES_SETTINGS,
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR,
                ),
                "selectedNodes",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.ENSEMBLE_SETTINGS,
                    EnsemblesSettings.Ids.ENSEMBLES_DROPDOWN,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.VISUALIZATION_RADIO_ITEMS,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RESAMPLING_FREQUENCY_DROPDOWN,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.FILTER_REALIZATION_SETTINGS,
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SELECTOR,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.FILTER_REALIZATION_SETTINGS,
                    FilterRealizationSettings.Ids.STATISTICS_FROM_RADIO_ITEMS,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.ENSEMBLE_SETTINGS,
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLES_STORE,
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.TIME_SERIES_SETTINGS,
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS,
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "value",
            ),
        )
        @callback_typecheck
        # pylint: disable=too-many-branches,
        def _user_download_data(
            data_requested: Union[int, None],
            vectors: List[str],
            selected_ensembles: List[str],
            visualization: VisualizationOptions,
            resampling_frequency_value: str,
            selected_realizations: List[int],
            statistics_from: StatisticsFromOptions,
            delta_ensembles: List[DeltaEnsemble],
            vector_calculator_expressions: List[ExpressionInfo],
            relative_date_value: Optional[str],
        ) -> Union[EncodedFile, str]:
            """Callback to download data based on selections

            Retrieve vector data based on selected visualizations and filtered realizations

            NOTE:
            * Does not group based on "Group By" - data is stored per vector
            * All statistics included - no filtering on statistics selections
            * No history vector
            * No observation data
            """
            if data_requested is None:
                raise PreventUpdate

            if not isinstance(selected_ensembles, list):
                raise TypeError("ensembles should always be of type list")

            if vectors is None:
                vectors = self._initial_selected_vectors

            # Retrieve the selected expressions
            selected_expressions = get_selected_expressions(
                vector_calculator_expressions, vectors
            )

            # Convert from string values to strongly typed
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )
            relative_date: Optional[datetime.datetime] = (
                None
                if relative_date_value is None
                else datetime_utils.from_str(relative_date_value)
            )

            # Create dict of derived vectors accessors for selected ensembles
            derived_vectors_accessors: Dict[
                str, DerivedVectorsAccessor
            ] = create_derived_vectors_accessor_dict(
                ensembles=selected_ensembles,
                vectors=vectors,
                provider_set=self._input_provider_set,
                expressions=selected_expressions,
                delta_ensembles=delta_ensembles,
                resampling_frequency=resampling_frequency,
                relative_date=relative_date,
            )

            # Dict with vector name as key and dataframe data as value
            vector_dataframe_dict: Dict[str, pd.DataFrame] = {}

            # Get all realizations if statistics across all realizations are requested
            is_statistics_from_all_realizations = (
                statistics_from == StatisticsFromOptions.ALL_REALIZATIONS
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

                # Retrieve vectors data from accessor
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

                # Append data for each vector
                for vectors_df in vectors_df_list:
                    # Ensure rows of data
                    if not vectors_df.shape[0]:
                        continue

                    vector_names = [
                        elm for elm in vectors_df.columns if elm not in ["DATE", "REAL"]
                    ]

                    if visualization in [
                        VisualizationOptions.REALIZATIONS,
                        VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    ]:
                        # NOTE: Should in theory not have situation with query of all realizations
                        # if not wanted
                        vectors_df_filtered = (
                            vectors_df
                            if realizations_query
                            else vectors_df[
                                vectors_df["REAL"].isin(selected_realizations)
                            ]
                        )
                        for vector in vector_names:
                            vector_df = vectors_df_filtered[["DATE", "REAL", vector]]
                            row_count = vector_df.shape[0]
                            ensemble_name_list = [ensemble] * row_count
                            vector_df.insert(
                                loc=0, column="ENSEMBLE", value=ensemble_name_list
                            )

                            if is_per_interval_or_per_day_vector(vector):
                                vector_df["DATE"] = vector_df["DATE"].apply(
                                    datetime_to_intervalstr, freq=resampling_frequency
                                )

                            vector_key = vector + "_realizations"
                            if vector_dataframe_dict.get(vector_key) is None:
                                vector_dataframe_dict[vector_key] = vector_df
                            else:
                                vector_dataframe_dict[vector_key] = pd.concat(
                                    [vector_dataframe_dict[vector_key], vector_df],
                                    ignore_index=True,
                                    axis=0,
                                )

                    if visualization in [
                        VisualizationOptions.STATISTICS,
                        VisualizationOptions.FANCHART,
                        VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    ]:
                        vectors_statistics_df = create_vectors_statistics_df(vectors_df)

                        for vector in vector_names:
                            vector_statistics_df = vectors_statistics_df[
                                ["DATE", vector]
                            ]
                            row_count = vector_statistics_df.shape[0]
                            ensemble_name_list = [ensemble] * row_count
                            vector_statistics_df.insert(
                                loc=0, column="ENSEMBLE", value=ensemble_name_list
                            )

                            vector_key = vector + "_statistics"

                            if is_per_interval_or_per_day_vector(vector):
                                # Copy df to prevent SettingWithCopyWarning
                                vector_statistics_df = vector_statistics_df.copy()
                                vector_statistics_df["DATE"] = vector_statistics_df[
                                    "DATE"
                                ].apply(
                                    datetime_to_intervalstr, freq=resampling_frequency
                                )
                            if vector_dataframe_dict.get(vector_key) is None:
                                vector_dataframe_dict[vector_key] = vector_statistics_df
                            else:
                                vector_dataframe_dict[vector_key] = pd.concat(
                                    [
                                        vector_dataframe_dict[vector_key],
                                        vector_statistics_df,
                                    ],
                                    ignore_index=True,
                                    axis=0,
                                )

            # : is replaced with _ in filenames to stay within POSIX portable pathnames
            # (e.g. : is not valid in a Windows path)
            return WebvizPluginABC.plugin_data_compress(
                [
                    {
                        "filename": f"{vector.replace(':', '_')}.csv",
                        "content": df.to_csv(index=False),
                    }
                    for vector, df in vector_dataframe_dict.items()
                ]
            )

        @callback(
            Output(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "options",
            ),
            Output(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "value",
            ),
            Output(
                self.settings_group_unique_id(
                    SubplotView.Ids.VISUALIZATION_SETTINGS,
                    VisualizationSettings.Ids.PLOT_TRACE_OPTIONS_CHECKLIST,
                ),
                "style",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RESAMPLING_FREQUENCY_DROPDOWN,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "options",
            ),
            State(
                self.settings_group_unique_id(
                    SubplotView.Ids.RESAMPLING_FREQUENCY_SETTINGS,
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN,
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_relative_date_dropdown_and_trace_options_style(
            resampling_frequency_value: str,
            relative_date_value: Optional[str],
            current_relative_date_options: List[Dict[str, str]],
            current_relative_date_value: Optional[str],
        ) -> Tuple[List[Dict[str, str]], Optional[str], Dict[str, str]]:
            """This callback updates dropdown based on selected resampling frequency selection
            and hide trace options (History and Observation) when a relative date is selected.

            If dates are not existing for a provider, the data accessor must handle invalid
            relative date selection!
            """
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )
            dates_union = self._input_provider_set.all_dates(resampling_frequency)

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

            # Convert to Optional[datetime.datetime]
            relative_date: Optional[datetime.datetime] = (
                None
                if relative_date_value is None
                else datetime_utils.from_str(relative_date_value)
            )
            trace_options_style = (
                {"display": "none"} if relative_date else {"display": "block"}
            )

            return (
                new_relative_date_options,
                new_relative_date_value,
                trace_options_style,
            )
