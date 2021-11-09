from typing import Callable, Dict, List, Optional, Tuple

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State

from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    Frequency,
)
from webviz_subsurface._utils.unique_theming import unique_colors
from webviz_subsurface.plugins._simulation_time_series.provider_set import ProviderSet

from .types import (
    DeltaEnsembleNamePair,
    create_delta_ensemble_names,
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)
from .selected_provider_set_model import SelectedProviderSetModel
from .graph_figure_builder import GraphFigureBuilder
from .utils.trace_line_shape import get_simulation_line_shape
from .utils.from_timeseries_cumulatives import (
    get_cumulative_vector_name,
    is_interval_or_average_vector,
)


from .main_view import ViewElements


def controller_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    input_provider_set: ProviderSet,
    theme: WebvizConfigTheme,
    sampling: str,  # TODO: Remove and use only resampling_frequency?
    initial_selected_vectors: List[str],
    observations: dict,
    resampling_frequency: Optional[Frequency],
    line_shape_fallback: str = "linear",
) -> None:
    @app.callback(
        Output(get_uuid(ViewElements.GRAPH), "figure"),
        [
            Input(
                get_uuid(ViewElements.VECTOR_SELECTOR),
                "selectedNodes",
            ),
            Input(get_uuid(ViewElements.ENSEMBLES_DROPDOWN), "value"),
            Input(
                get_uuid(ViewElements.VISUALIZATION_RADIO_ITEMS),
                "value",
            ),
            Input(
                get_uuid(ViewElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                "value",
            ),
            Input(
                get_uuid(ViewElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
                "value",
            ),
            Input(
                get_uuid(ViewElements.PLOT_TRACE_OPTIONS_CHECKLIST),
                "value",
            ),
        ],
        [
            State(
                get_uuid(ViewElements.CREATED_DELTA_ENSEMBLES),
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
        delta_ensembles: List[DeltaEnsembleNamePair],
        # cumulative_interval: str,
    ) -> dict:
        """Callback to update all graphs based on selections

        TODO:
        - Should be a "pure" controller in model-view-control? I.e. pass into a "model"
        and retrieve states/arguments to pass on to a "view"?
        - Convert dash input/state to types, delegate to model and retreive data for providing
        to  graphing
        """

        # Convert from string values to enum types
        visualization = VisualizationOptions(visualization_value)
        statistics_options = [
            StatisticsOptions(elm) for elm in statistics_option_values
        ]
        fanchart_options = [FanchartOptions(elm) for elm in fanchart_option_values]
        trace_options = [TraceOptions(elm) for elm in trace_option_values]

        if not isinstance(selected_ensembles, list):
            raise TypeError("ensembles should always be of type list")

        if vectors is None:
            vectors = initial_selected_vectors

        # Filter selected delta ensembles
        selected_ensembles_model = SelectedProviderSetModel(
            input_provider_set,
            selected_ensembles,
            delta_ensembles,
            resampling_frequency,
        )

        # Titles for subplots TODO: Verify vector existing?
        vector_titles: Dict[str, str] = {
            elm: selected_ensembles_model.create_vector_plot_title(elm)
            for elm in vectors
        }

        # TODO: Create unique colors based on all ensembles, i.e. union of
        # ensemble_set_model.ensemble_names() and create_delta_ensemble_names(delta_ensembles)
        # Now color can change when changing selected ensembles?
        ensemble_colors = unique_colors(
            selected_ensembles_model.provider_names(), theme
        )

        figure_builder = GraphFigureBuilder(
            vectors, vector_titles, ensemble_colors, sampling, theme
        )

        # TODO: How to handle vector metadata the best way?
        vector_line_shapes: Dict[str, str] = {
            vector: get_simulation_line_shape(
                line_shape_fallback,
                vector,
                selected_ensembles_model.vector_metadata(vector),
            )
            for vector in vectors
        }

        # Plotting per ensemble
        for ensemble in selected_ensembles_model.provider_names():
            provider_vector_names = selected_ensembles_model.provider_vector_names(
                ensemble
            )

            # Separate provider vectors and calculation vectors
            # TODO: Consider creating selected_ensembles_model.set_selected_vectors(vectors: List[str])
            # and let model handled ensemble vectors and cumulative vectors state internally.
            provider_vectors = [
                elm
                for elm in vectors
                if not is_interval_or_average_vector(elm)
                and elm in provider_vector_names
            ]
            interval_and_average_vectors = [
                elm
                for elm in vectors
                if is_interval_or_average_vector(elm)
                and get_cumulative_vector_name(elm) in provider_vector_names
            ]

            if not provider_vectors and not interval_and_average_vectors:
                continue

            vectors_df = None
            interval_and_average_vectors_df = None
            if provider_vectors:
                vectors_df = selected_ensembles_model.get_provider_vectors_df(
                    ensemble, provider_vectors
                )
            if interval_and_average_vectors:
                interval_and_average_vectors_df = (
                    selected_ensembles_model.create_interval_and_average_vectors_df(
                        ensemble, interval_and_average_vectors, sampling
                    )
                )

            if visualization == VisualizationOptions.REALIZATIONS:
                if vectors_df is not None:
                    figure_builder.add_realizations_traces(
                        vectors_df, ensemble, vector_line_shapes
                    )
                if interval_and_average_vectors_df is not None:
                    figure_builder.add_realizations_traces(
                        interval_and_average_vectors_df,
                        ensemble,
                        vector_line_shapes,
                        add_legend=not provider_vectors,
                    )
            if visualization == VisualizationOptions.STATISTICS:
                if vectors_df is not None:
                    vectors_statistics_df = (
                        selected_ensembles_model.create_statistics_df(vectors_df)
                    )
                    figure_builder.add_statistics_traces(
                        vectors_statistics_df,
                        ensemble,
                        statistics_options,
                        vector_line_shapes,
                    )
                if interval_and_average_vectors_df is not None:
                    vectors_statistics_df = (
                        selected_ensembles_model.create_statistics_df(
                            interval_and_average_vectors_df
                        )
                    )
                    figure_builder.add_statistics_traces(
                        vectors_statistics_df,
                        ensemble,
                        statistics_options,
                        vector_line_shapes,
                        add_legend=not provider_vectors,
                    )

            if visualization == VisualizationOptions.FANCHART:
                if vectors_df is not None:
                    vectors_statistics_df = (
                        selected_ensembles_model.create_statistics_df(vectors_df)
                    )
                    figure_builder.add_fanchart_traces(
                        vectors_statistics_df,
                        ensemble,
                        fanchart_options,
                        vector_line_shapes,
                    )
                if interval_and_average_vectors_df is not None:
                    vectors_statistics_df = (
                        selected_ensembles_model.create_statistics_df(
                            interval_and_average_vectors_df
                        )
                    )
                    figure_builder.add_fanchart_traces(
                        vectors_statistics_df,
                        ensemble,
                        fanchart_options,
                        vector_line_shapes,
                        add_legend=not provider_vectors,
                    )

        if TraceOptions.VECTOR_OBSERVATIONS in trace_options:
            for vector in vectors:
                vector_observations = observations.get(vector)
                if vector_observations:
                    figure_builder.add_vector_observations(vector, vector_observations)

        if (
            TraceOptions.HISTORY in trace_options
            and len(selected_ensembles_model.provider_names()) > 0
        ):
            # NOTE: Retrieve historical vector from first ensemble
            # Name and provider from first selected ensemble
            ensemble = selected_ensembles_model.provider_names()[0]
            vector_names = selected_ensembles_model.provider_vector_names(ensemble)

            provider_vectors = [elm for elm in vectors if elm in vector_names]

            history_vectors_df = selected_ensembles_model.create_history_vectors_df(
                ensemble, provider_vectors
            )
            # TODO: Handle check of non-empty dataframe better!
            if not history_vectors_df.empty and "DATE" in history_vectors_df.columns:
                figure_builder.add_history_traces(
                    history_vectors_df, vector_line_shapes
                )

        return figure_builder.get_figure()

    # TODO: Implement callback
    # @app.callback()
    # def _user_download_data() -> None:
    #     raise NotImplementedError()

    @app.callback(
        [
            Output(
                get_uuid(ViewElements.PLOT_STATISTICS_OPTIONS_CHECKLIST),
                "style",
            ),
            Output(
                get_uuid(ViewElements.PLOT_FANCHART_OPTIONS_CHECKLIST),
                "style",
            ),
        ],
        [
            Input(
                get_uuid(ViewElements.VISUALIZATION_RADIO_ITEMS),
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
                get_uuid(ViewElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            Output(
                get_uuid(ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE),
                "data",
            ),
            Output(
                get_uuid(ViewElements.ENSEMBLES_DROPDOWN),
                "options",
            ),
        ],
        [
            Input(
                get_uuid(ViewElements.DELTA_ENSEMBLE_ADD_BUTTON),
                "n_clicks",
            )
        ],
        [
            State(
                get_uuid(ViewElements.CREATED_DELTA_ENSEMBLES),
                "data",
            ),
            State(
                get_uuid(ViewElements.DELTA_ENSEMBLE_A_DROPDOWN),
                "value",
            ),
            State(
                get_uuid(ViewElements.DELTA_ENSEMBLE_B_DROPDOWN),
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
            get_uuid(ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN),
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
