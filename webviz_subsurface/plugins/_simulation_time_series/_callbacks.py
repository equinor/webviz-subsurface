from typing import Callable, Dict, List, Tuple

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import pandas as pd

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
    create_vector_plot_title_from_provider_set,
)
from .utils.vector_statistics import create_vectors_statistics_df
from .utils.history_vectors import create_history_vectors_df

# TODO: Consider adding: presampled_frequency: Optional[Frequency] argument for use when
# providers are presampled. To keep track of sampling frequency, and not depend on dropdown
# value for ViewElements.RESAMPLING_FREQUENCY_DROPDOWN (dropdown disabled when providers are
# presampled)
# pylint: disable = too-many-branches, too-many-locals, too-many-statements
def plugin_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    input_provider_set: ProviderSet,
    theme: WebvizConfigTheme,
    initial_selected_vectors: List[str],
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
        ],
        [
            State(
                get_uuid(LayoutElements.CREATED_DELTA_ENSEMBLES),
                "data",
            )
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
        delta_ensembles: List[DeltaEnsembleNamePair],
    ) -> dict:
        """Callback to update all graphs based on selections

        * De-serialize from JSON serializable format to strongly typed and filtered format
        * Business logic with SelectedProviderSet, ProviderVectorDataHandler and utility functions
        with "strongly typed" and filtered input format
        * Create/build prop serialization in FigureBuilder by use of business logic data
        """

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

        if vectors is None:
            vectors = initial_selected_vectors

        # Filter selected delta ensembles
        selected_provider_set = create_selected_provider_set(
            input_provider_set, selected_ensembles, delta_ensembles
        )

        # Titles for subplots TODO: Verify vector existing?
        vector_titles: Dict[str, str] = {
            vector: create_vector_plot_title_from_provider_set(
                selected_provider_set, vector
            )
            for vector in vectors
        }

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
                expressions=None,
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
                get_uuid(LayoutElements.DELTA_ENSEMBLE_ADD_BUTTON),
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

        table_data = create_delta_ensemble_table_column_data(
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


def create_delta_ensemble_table_column_data(
    column_name: str, ensemble_names: List[str]
) -> List[Dict[str, str]]:
    return [{column_name: elm} for elm in ensemble_names]
