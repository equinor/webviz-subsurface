from typing import Callable, Dict, List, Optional, Tuple

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State

from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from .types import (
    DeltaEnsembleNamePair,
    delta_ensemble_names,
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)
from .data_model import DataModel
from .graph_figure_builder import GraphFigureBuilder

from .utils.trace_line_shape import get_simulation_line_shape


from .main_view import ViewElements


# pylint: disable=too-many-statements
def controller_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    provider_set: Dict[str, EnsembleSummaryProvider],
    theme: WebvizConfigTheme,
    sampling: str,  # TODO: Remove and use only resampling_frequency?
    resampling_frequency: Optional[Frequency],
    selected_vectors: List[str],
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
    # pylint: disable=too-many-locals, too-many-branches
    def _update_graph(
        vectors: List[str],
        selected_ensembles: List[str],
        visualization_value: str,
        statistics_option_values: List[str],
        fanchart_option_values: List[str],
        trace_option_values: List[str],
        delta_ensembles: List[DeltaEnsembleNamePair],
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

        # TODO: Add AVG_ and INTVL_ vectors
        # TODO: Add obsevations

        if not isinstance(selected_ensembles, list):
            raise TypeError("ensembles should always be of type list")

        if vectors is None:
            vectors = selected_vectors

        # Filter selected delta ensembles
        # selected_delta_ensembles = [
        #     elm
        #     for elm in delta_ensembles
        #     if delta_ensemble_name(elm) in selected_ensembles
        # ]
        # data_model = DataModel(
        #     provider_set, selected_delta_ensembles, theme
        # )

        data_model = DataModel(provider_set, delta_ensembles, theme)
        ensemble_provider_dict = data_model.get_selected_ensemble_providers(
            selected_ensembles
        )

        # Titles for subplots TODO: Verify vector existing?
        vector_titles: Dict[str, str] = {
            elm: data_model.create_vector_plot_title(elm) for elm in vectors
        }

        # TODO: Filter with only selected ensembles?
        ensemble_colors = data_model.get_unique_ensemble_colors()

        figure_builder = GraphFigureBuilder(
            vectors, vector_titles, ensemble_colors, sampling
        )

        # Plotting per ensemble
        for ensemble, provider in ensemble_provider_dict.items():
            # Filter vectors for provider
            vectors_filtered = [
                elm for elm in vectors if elm in provider.vector_names()
            ]
            if len(vectors_filtered) <= 0:
                continue

            resampling_freq = (
                resampling_frequency if provider.supports_resampling() else None
            )

            ensemble_vectors_df = provider.get_vectors_df(
                vectors_filtered, resampling_freq
            )

            vector_line_shapes: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    line_shape_fallback, vector, provider.vector_metadata(vector)
                )
                for vector in vectors_filtered
            }

            if visualization == VisualizationOptions.REALIZATIONS:
                figure_builder.add_realizations_traces(
                    ensemble_vectors_df, ensemble, vector_line_shapes
                )
            if visualization == VisualizationOptions.STATISTICS:
                vectors_df = data_model.create_statistics_df(
                    ensemble, vectors_filtered, resampling_freq
                )
                figure_builder.add_statistics_traces(
                    vectors_df, ensemble, statistics_options, vector_line_shapes
                )
            if visualization == VisualizationOptions.FANCHART:
                vectors_df = data_model.create_statistics_df(
                    ensemble, vectors_filtered, resampling_freq
                )

                figure_builder.add_fanchart_traces(
                    vectors_df, ensemble, fanchart_options, vector_line_shapes
                )

        # NOTE: Retrieve historical vector from first ensemble
        if TraceOptions.HISTORY in trace_options and len(ensemble_provider_dict) > 0:
            # Name and provider from first selected ensemble
            name, provider = list(ensemble_provider_dict.items())[0]

            vectors_filtered = [
                elm for elm in vectors if elm in provider.vector_names()
            ]

            vector_line_shapes_2: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    line_shape_fallback, vector, provider.vector_metadata(vector)
                )
                for vector in vectors_filtered
            }

            resampling_freq = (
                resampling_frequency if provider.supports_resampling() else None
            )

            history_vectors_df = data_model.create_history_vectors_df(
                name, vectors_filtered, resampling_freq
            )
            figure_builder.add_history_traces(history_vectors_df, vector_line_shapes_2)

        # # Keep uirevision (e.g. zoom) for unchanged data.
        # figure.update_xaxes(uirevision="locked")  # Time axis state kept
        # for i, vector in enumerate(vectors, start=1):
        #     figure.update_yaxes(row=i, col=1, uirevision=vector)

        return figure_builder.get_figure()

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
        new_delta_ensemble_names = delta_ensemble_names(new_delta_ensembles)

        table_data = create_delta_ensemble_table_column_data(
            get_uuid(ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN),
            new_delta_ensemble_names,
        )

        ensemble_options = [
            {"label": ensemble, "value": ensemble} for ensemble in provider_set.keys()
        ]
        for elm in new_delta_ensemble_names:
            ensemble_options.append({"label": elm, "value": elm})

        return (new_delta_ensembles, table_data, ensemble_options)


def create_delta_ensemble_table_column_data(
    column_name: str, ensemble_names: List[str]
) -> List[Dict[str, str]]:
    return [{column_name: elm} for elm in ensemble_names]
