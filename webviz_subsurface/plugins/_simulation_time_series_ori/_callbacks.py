# pylint: disable=too-many-lines
import copy
import datetime
from typing import Callable, Dict, List, Optional, Tuple, Union

import dash
import pandas as pd
import webviz_subsurface_components as wsc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile, WebvizPluginABC
from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface_components import (
    ExpressionInfo,
    ExternalParseData,
    VectorDefinition,
)

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.formatting import printable_int_list
from webviz_subsurface._utils.unique_theming import unique_colors
from webviz_subsurface._utils.vector_calculator import (
    add_expressions_to_vector_selector_data,
    get_selected_expressions,
    get_vector_definitions_from_expressions,
)
from webviz_subsurface._utils.vector_selector import (
    is_vector_name_in_vector_selector_data,
)

from ._layout import LayoutElements
from ._property_serialization import (
    EnsembleSubplotBuilder,
    GraphFigureBuilderBase,
    VectorSubplotBuilder,
)
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
from .utils.delta_ensemble_utils import create_delta_ensemble_names
from .utils.derived_ensemble_vectors_accessor_utils import (
    create_derived_vectors_accessor_dict,
)
from .utils.from_timeseries_cumulatives import (
    datetime_to_intervalstr,
    is_per_interval_or_per_day_vector,
)
from .utils.history_vectors import create_history_vectors_df
from .utils.provider_set_utils import create_vector_plot_titles_from_provider_set
from .utils.trace_line_shape import get_simulation_line_shape
from .utils.vector_statistics import create_vectors_statistics_df


# pylint: disable = too-many-arguments, too-many-branches, too-many-locals, too-many-statements
def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
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
) -> None:
    # TODO: Consider adding: presampled_frequency: Optional[Frequency] argument for use when
    # providers are presampled. To keep track of sampling frequency, and not depend on dropdown
    # value for ViewElements.RESAMPLING_FREQUENCY_DROPDOWN (dropdown disabled when providers are
    # presampled)
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
                get_uuid(LayoutElements.SUBPLOT_OWNER_OPTIONS_RADIO_ITEMS),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                "value",
            ),
            Input(get_uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR), "value"),
            Input(
                get_uuid(LayoutElements.STATISTICS_FROM_RADIO_ITEMS),
                "value",
            ),
            Input(
                get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN),
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
            State(get_uuid(LayoutElements.ENSEMBLES_DROPDOWN), "options"),
        ],
    )
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
        graphs data has changed and re-render of graph is necessary. E.g. when a selected expression
        from the VectorCalculator gets edited without changing the expression name - i.e.
        VectorSelector selectedNodes remain unchanged.
        """
        if not isinstance(selected_ensembles, list):
            raise TypeError("ensembles should always be of type list")

        if vectors is None:
            vectors = initial_selected_vectors

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
        resampling_frequency = Frequency.from_string_value(resampling_frequency_value)
        all_ensemble_names = [option["value"] for option in ensemble_dropdown_options]
        statistics_from_option = StatisticsFromOptions(statistics_calculated_from_value)

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
            trigger_id == get_uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR)
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
            provider_set=input_provider_set,
            expressions=selected_expressions,
            delta_ensembles=delta_ensembles,
            resampling_frequency=resampling_frequency,
            relative_date=relative_date,
        )

        # TODO: How to get metadata for calculated vector?
        vector_line_shapes: Dict[str, str] = {
            vector: get_simulation_line_shape(
                line_shape_fallback,
                vector,
                input_provider_set.vector_metadata(vector),
            )
            for vector in vectors
        }

        figure_builder: GraphFigureBuilderBase
        if subplot_owner is SubplotGroupByOptions.VECTOR:
            # Create unique colors based on all ensemble names to preserve consistent colors
            ensemble_colors = unique_colors(all_ensemble_names, theme)
            vector_titles = create_vector_plot_titles_from_provider_set(
                vectors,
                selected_expressions,
                input_provider_set,
                user_defined_vector_definitions,
                resampling_frequency,
            )
            figure_builder = VectorSubplotBuilder(
                vectors,
                vector_titles,
                ensemble_colors,
                resampling_frequency,
                vector_line_shapes,
                theme,
            )
        elif subplot_owner is SubplotGroupByOptions.ENSEMBLE:
            vector_colors = unique_colors(vectors, theme)
            figure_builder = EnsembleSubplotBuilder(
                vectors,
                selected_ensembles,
                vector_colors,
                resampling_frequency,
                vector_line_shapes,
                theme,
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
                    accessor.get_provider_vectors_df(realizations=realizations_query)
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
                        else vectors_df[vectors_df["REAL"].isin(selected_realizations)],
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
                if visualization == VisualizationOptions.STATISTICS_AND_REALIZATIONS:
                    # Configure line width and color scaling to easier separate
                    # statistics traces and realization traces.
                    # Show selected realizations - only filter df if realizations filter
                    # query is not performed
                    figure_builder.add_realizations_traces(
                        vectors_df
                        if realizations_query
                        else vectors_df[vectors_df["REAL"].isin(selected_realizations)],
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
                for name, provider in input_provider_set.items()
                if name in selected_ensembles
            }
        )

        # Do not add observations if only delta ensembles are selected
        is_only_delta_ensembles = (
            len(selected_input_providers.names()) == 0
            and len(derived_vectors_accessors) > 0
        )
        if (
            observations
            and TraceOptions.OBSERVATIONS in trace_options
            and not is_only_delta_ensembles
            and not relative_date
        ):
            for vector in vectors:
                vector_observations = observations.get(vector)
                if vector_observations:
                    figure_builder.add_vector_observations(vector, vector_observations)

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
                                history_vectors_df,
                                name,
                            )

        # Create legends when all data is added to figure
        figure_builder.create_graph_legends()

        return figure_builder.get_serialized_figure()

    @app.callback(
        get_data_output,
        [get_data_requested],
        [
            State(
                get_uuid(LayoutElements.VECTOR_SELECTOR),
                "selectedNodes",
            ),
            State(get_uuid(LayoutElements.ENSEMBLES_DROPDOWN), "value"),
            State(
                get_uuid(LayoutElements.VISUALIZATION_RADIO_ITEMS),
                "value",
            ),
            State(
                get_uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                "value",
            ),
            State(get_uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR), "value"),
            State(
                get_uuid(LayoutElements.STATISTICS_FROM_RADIO_ITEMS),
                "value",
            ),
            State(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            State(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS),
                "data",
            ),
            State(
                get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN),
                "value",
            ),
        ],
    )
    def _user_download_data(
        data_requested: Union[int, None],
        vectors: List[str],
        selected_ensembles: List[str],
        visualization_value: str,
        resampling_frequency_value: str,
        selected_realizations: List[int],
        statistics_calculated_from_value: str,
        delta_ensembles: List[DeltaEnsemble],
        vector_calculator_expressions: List[ExpressionInfo],
        relative_date_value: str,
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
            vectors = initial_selected_vectors

        # Retrieve the selected expressions
        selected_expressions = get_selected_expressions(
            vector_calculator_expressions, vectors
        )

        # Convert from string values to strongly typed
        visualization = VisualizationOptions(visualization_value)
        resampling_frequency = Frequency.from_string_value(resampling_frequency_value)
        statistics_from_option = StatisticsFromOptions(statistics_calculated_from_value)

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
            provider_set=input_provider_set,
            expressions=selected_expressions,
            delta_ensembles=delta_ensembles,
            resampling_frequency=resampling_frequency,
            relative_date=relative_date,
        )

        # Dict with vector name as key and dataframe data as value
        vector_dataframe_dict: Dict[str, pd.DataFrame] = {}

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

            # Retrive vectors data from accessor
            vectors_df_list: List[pd.DataFrame] = []
            if accessor.has_provider_vectors():
                vectors_df_list.append(
                    accessor.get_provider_vectors_df(realizations=realizations_query)
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
                        else vectors_df[vectors_df["REAL"].isin(selected_realizations)]
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
                        vector_statistics_df = vectors_statistics_df[["DATE", vector]]
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
                            ].apply(datetime_to_intervalstr, freq=resampling_frequency)
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
    def _update_statistics_options_layout(selected_visualization: str) -> List[dict]:
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
        existing_delta_ensembles: List[DeltaEnsemble],
        ensemble_a: str,
        ensemble_b: str,
    ) -> Tuple[List[DeltaEnsemble], List[Dict[str, str]], List[Dict[str, str]]]:
        if n_clicks is None or n_clicks <= 0:
            raise PreventUpdate

        delta_ensemble = DeltaEnsemble(ensemble_a=ensemble_a, ensemble_b=ensemble_b)
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
        Output(get_uuid(LayoutElements.VECTOR_CALCULATOR_DIALOG), "open"),
        [
            Input(get_uuid(LayoutElements.VECTOR_CALCULATOR_OPEN_BUTTON), "n_clicks"),
        ],
        [State(get_uuid(LayoutElements.VECTOR_CALCULATOR_DIALOG), "open")],
    )
    def _toggle_vector_calculator_dialog_open(
        n_open_clicks: int, is_open: bool
    ) -> bool:
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
        Input(get_uuid(LayoutElements.VECTOR_CALCULATOR_DIALOG), "open"),
        [
            State(
                get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG),
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
        if is_dialog_open or (new_expressions == current_expressions):
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
        new_custom_vector_definitions = get_vector_definitions_from_expressions(
            new_expressions
        )
        for key, value in custom_vector_definitions_base.items():
            if key not in new_custom_vector_definitions:
                new_custom_vector_definitions[key] = value

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
            get_uuid(LayoutElements.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG),
            "data",
        ),
        Input(get_uuid(LayoutElements.VECTOR_CALCULATOR), "expressions"),
    )
    def _update_vector_calculator_expressions_when_dialog_open(
        expressions: List[ExpressionInfo],
    ) -> list:
        new_expressions: List[ExpressionInfo] = [
            elm for elm in expressions if elm["isValid"]
        ]
        return new_expressions

    @app.callback(
        Output(get_uuid(LayoutElements.REALIZATIONS_FILTER_SPAN), "children"),
        Input(get_uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR), "value"),
    )
    def _update_realization_range(realizations: List[int]) -> Optional[str]:
        if not realizations:
            raise PreventUpdate

        realizations_filter_text = printable_int_list(realizations)

        return realizations_filter_text

    @app.callback(
        [
            Output(get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN), "options"),
            Output(get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN), "value"),
        ],
        [
            Input(
                get_uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                "value",
            ),
        ],
        [
            State(get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN), "options"),
            State(get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN), "value"),
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
        resampling_frequency = Frequency.from_string_value(resampling_frequency_value)
        dates_union = input_provider_set.all_dates(resampling_frequency)

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

    @app.callback(
        [
            Output(
                get_uuid(LayoutElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                "style",
            ),
        ],
        [
            Input(
                get_uuid(LayoutElements.RELATIVE_DATE_DROPDOWN),
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
