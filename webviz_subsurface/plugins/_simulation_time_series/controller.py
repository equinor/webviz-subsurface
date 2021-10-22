from typing import Callable, Dict, List, Tuple

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State

from webviz_config._theme_class import WebvizConfigTheme
from .types import (
    DeltaEnsembleNamePair,
    create_delta_ensemble_names,
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)
from .selected_ensembles_model import SelectedEnsemblesModel
from .graph_figure_builder import GraphFigureBuilder

from .utils.trace_line_shape import get_simulation_line_shape


from .main_view import ViewElements
from .models.ensemble_set_model import EnsembleSetModel


# pylint: disable=too-many-statements
def controller_callbacks(
    app: dash.Dash,
    get_uuid: Callable,
    ensemble_set_model: EnsembleSetModel,
    theme: WebvizConfigTheme,
    sampling: str,  # TODO: Remove and use only resampling_frequency?
    initial_selected_vectors: List[str],
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
            vectors = initial_selected_vectors

        # Filter selected delta ensembles
        selected_ensembles_model = SelectedEnsemblesModel(
            ensemble_set_model, selected_ensembles, delta_ensembles
        )

        selected_ensembles_providers = selected_ensembles_model.ensemble_provider_set()

        # Titles for subplots TODO: Verify vector existing?
        vector_titles: Dict[str, str] = {
            elm: selected_ensembles_model.create_vector_plot_title(elm)
            for elm in vectors
        }

        # TODO: Create unique colors based on all ensembles, i.e. union of
        # ensemble_set_model.ensemble_names() and create_delta_ensemble_names(delta_ensembles)
        # Now color can change when chaning selected colors?
        ensemble_colors = selected_ensembles_model.get_unique_ensemble_colors(theme)

        figure_builder = GraphFigureBuilder(
            vectors, vector_titles, ensemble_colors, sampling
        )

        vector_line_shapes: Dict[str, str] = {
            vector: get_simulation_line_shape(
                line_shape_fallback,
                vector,
                selected_ensembles_model.vector_metadata(vector),
            )
            for vector in vectors
        }

        # Plotting per ensemble
        for ensemble, provider in selected_ensembles_providers.items():
            # Filter vectors for provider
            ensemble_vectors = [
                elm for elm in vectors if elm in provider.vector_names()
            ]
            if len(ensemble_vectors) <= 0:
                continue

            if visualization == VisualizationOptions.REALIZATIONS:
                resampling_freq = (
                    ensemble_set_model.resampling_frequency()
                    if provider.supports_resampling()
                    else None
                )
                vectors_df = provider.get_vectors_df(ensemble_vectors, resampling_freq)
                figure_builder.add_realizations_traces(
                    vectors_df, ensemble, vector_line_shapes
                )
            if visualization == VisualizationOptions.STATISTICS:
                vectors_df = selected_ensembles_model.create_statistics_df(
                    ensemble, ensemble_vectors
                )
                figure_builder.add_statistics_traces(
                    vectors_df, ensemble, statistics_options, vector_line_shapes
                )
            if visualization == VisualizationOptions.FANCHART:
                vectors_df = selected_ensembles_model.create_statistics_df(
                    ensemble, ensemble_vectors
                )
                figure_builder.add_fanchart_traces(
                    vectors_df, ensemble, fanchart_options, vector_line_shapes
                )

        # NOTE: Retrieve historical vector from first ensemble
        if (
            TraceOptions.HISTORY in trace_options
            and len(selected_ensembles_providers) > 0
        ):
            # Name and provider from first selected ensemble
            ensemble, provider = list(selected_ensembles_providers.items())[0]

            ensemble_vectors = [
                elm for elm in vectors if elm in provider.vector_names()
            ]

            history_vectors_df = selected_ensembles_model.create_history_vectors_df(
                ensemble, ensemble_vectors
            )
            figure_builder.add_history_traces(history_vectors_df, vector_line_shapes)

        figure_builder.set_keep_uirevision()
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
        new_delta_ensemble_names = create_delta_ensemble_names(new_delta_ensembles)

        table_data = create_delta_ensemble_table_column_data(
            get_uuid(ViewElements.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN),
            new_delta_ensemble_names,
        )

        ensemble_options = [
            {"label": ensemble, "value": ensemble}
            for ensemble in ensemble_set_model.ensemble_names()
        ]
        for elm in new_delta_ensemble_names:
            ensemble_options.append({"label": elm, "value": elm})

        return (new_delta_ensembles, table_data, ensemble_options)


def create_delta_ensemble_table_column_data(
    column_name: str, ensemble_names: List[str]
) -> List[Dict[str, str]]:
    return [{column_name: elm} for elm in ensemble_names]
