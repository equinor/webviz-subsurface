from typing import Callable, Dict, List, Optional, Tuple

import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from plotly.subplots import make_subplots

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

from .utils.trace_line_shape import get_simulation_line_shape

from .utils.ensemble_vectors_traces import (
    create_ensemble_vectors_fanchart_traces,
    create_ensemble_vectors_realizations_traces,
    create_ensemble_vectors_statistics_traces,
)
from .utils.history_vectors_traces import create_historical_vectors_traces


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
        ensemble_colors = data_model.get_unique_ensemble_colors()

        # Titles for subplots TODO: Verify vector existing?
        titles = [data_model.create_vector_plot_title(elm) for elm in vectors]

        # TODO: Handle traces with figure/graph utility or handler? See LinePlotterFMU
        # Make a plotly subplot figure
        figure = make_subplots(
            rows=max(1, len(vectors)),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=titles if titles else ["No vector selected"],
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

            ensemble_color = ensemble_colors.get(
                ensemble, ensemble_colors[list(ensemble_colors.keys())[0]]
            )

            vector_line_shapes: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    line_shape_fallback, vector, provider.vector_metadata(vector)
                )
                for vector in vectors_filtered
            }

            # Dictionary with vector name as key and list of ensemble traces as value
            vector_traces_dict: Dict[str, List[dict]] = {}
            if visualization == VisualizationOptions.REALIZATIONS:
                vector_traces_dict = create_ensemble_vectors_realizations_traces(
                    ensemble_vectors_df=ensemble_vectors_df,
                    color=ensemble_color,
                    ensemble=ensemble,
                    vector_line_shapes=vector_line_shapes,
                    interval=sampling,
                )
            if visualization == VisualizationOptions.STATISTICS:
                vector_traces_dict = create_ensemble_vectors_statistics_traces(
                    ensemble_vectors_df,
                    color=ensemble_color,
                    vector_line_shapes=vector_line_shapes,
                    ensemble=ensemble,
                    interval=sampling,
                    statistics_options=statistics_options,
                )
            if visualization == VisualizationOptions.FANCHART:
                vector_traces_dict = create_ensemble_vectors_fanchart_traces(
                    ensemble_vectors_df,
                    color=ensemble_color,
                    vector_line_shapes=vector_line_shapes,
                    ensemble=ensemble,
                    interval=sampling,
                    fanchart_options=fanchart_options,
                )

            # Add traces to figure
            for vector, traces in vector_traces_dict.items():
                subplot_index = vectors.index(vector) + 1 if vector in vectors else None
                if subplot_index is None:
                    continue
                figure.add_traces(traces, rows=subplot_index, cols=1)

        # NOTE: Retrieve historical vector from first ensemble
        if TraceOptions.HISTORY in trace_options and len(ensemble_provider_dict) > 0:
            # Provider from first ensemble
            provider = list(ensemble_provider_dict.values())[0]

            history_vector_line_shapes: Dict[str, str] = {
                vector: get_simulation_line_shape(
                    line_shape_fallback, vector, provider.vector_metadata(vector)
                )
                for vector in vectors
            }
            resampling_freq = (
                resampling_frequency if provider.supports_resampling() else None
            )
            historical_vectors_traces = create_historical_vectors_traces(
                provider, resampling_freq, vectors, history_vector_line_shapes
            )

            add_legend = True
            for vector, trace in historical_vectors_traces.items():
                subplot_index = vectors.index(vector) + 1 if vector in vectors else None
                if subplot_index is None:
                    continue
                # Add legend for one trace
                if add_legend:
                    trace["showlegend"] = True
                    add_legend = False
                figure.add_trace(trace, row=subplot_index, col=1)

        # Keep uirevision (e.g. zoom) for unchanged data.
        figure.update_xaxes(uirevision="locked")  # Time axis state kept
        for i, vector in enumerate(vectors, start=1):
            figure.update_yaxes(row=i, col=1, uirevision=vector)

        return figure.to_dict()

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
