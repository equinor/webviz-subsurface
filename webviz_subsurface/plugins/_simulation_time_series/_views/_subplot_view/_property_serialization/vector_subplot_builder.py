from typing import Dict, List, Optional, Set

import pandas as pd
from plotly.subplots import make_subplots
from webviz_config._theme_class import WebvizConfigTheme

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.colors import hex_to_rgb, rgb_to_str, scale_rgb_lightness

from .._types import FanchartOptions, StatisticsOptions
from .._utils.create_vector_traces_utils import (
    create_history_vector_trace,
    create_vector_fanchart_traces,
    create_vector_observation_traces,
    create_vector_realization_traces,
    create_vector_statistics_traces,
    render_hovertemplate,
)
from .graph_figure_builder_base import GraphFigureBuilderBase


class VectorSubplotBuilder(GraphFigureBuilderBase):
    """
    Figure builder for creating/building serializable Output property data
    for the callback. Where vector traces are added per ensemble, and subplots
    are categorized per vector among selected vectors.

    Contains functions for adding titles, graph data and retrieving the serialized
    data for callback Output property.

    `Input:`
    * selected_vectors: List[str] - list of selected vector names
    * vector_titles: Dict[str, str] - Dictionary with vector names as keys and plot titles as values
    * ensemble_colors: dict - Dictionary with ensemble names as keys and graph colors as values
    * sampling_frequency: Optional[Frequency] - Sampling frequency of data
    * vector_line_shapes: Dict[str,str] - Dictionary of vector names and line shapes
    * theme: Optional[WebvizConfigTheme] = None - Theme for plugin, given to graph figure
    * line_shape_fallback: str = "linear" - Lineshape fallback
    """

    def __init__(
        self,
        selected_vectors: List[str],
        vector_titles: Dict[str, str],
        ensemble_colors: dict,
        sampling_frequency: Optional[Frequency],
        vector_line_shapes: Dict[str, str],
        theme: Optional[WebvizConfigTheme] = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        # Init for base class
        super().__init__()

        self._selected_vectors = selected_vectors
        self._ensemble_colors = ensemble_colors
        self._sampling_frequency = sampling_frequency
        self._vector_line_shapes = vector_line_shapes
        self._line_shape_fallback = line_shape_fallback
        self._history_vector_color = "black"
        self._observation_color = "black"

        # Overwrite graph figure widget
        self._figure = make_subplots(
            rows=max(1, len(self._selected_vectors)),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=min(0.05, 1 / max(1, len(self._selected_vectors))),
            subplot_titles=[vector_titles.get(elm, elm) for elm in selected_vectors],
        )
        if theme:
            self._figure.update_layout(
                theme.create_themed_layout(self._figure.to_dict().get("layout", {}))
            )

        self._set_keep_uirevision()

        # Set for storing added ensembles
        self._added_ensemble_traces: List[str] = []

        # Status for added history vectors
        self._added_history_trace = False

        # Status for added observation traces
        self._added_observation_trace = False

    #############################################################################
    #
    # Public methods
    #
    #############################################################################

    def create_graph_legends(self) -> None:
        # Add legends for added ensembles
        for index, ensemble in enumerate(self._added_ensemble_traces, start=1):
            ensemble_legend_trace = {
                "name": ensemble,
                "x": [None],
                "y": [None],
                "legendgroup": ensemble,
                "showlegend": True,
                "visible": True,
                "mode": "lines",
                "line": {
                    "color": self._ensemble_colors.get(ensemble, "black"),
                },
                "legendrank": index,
            }
            self._figure.add_trace(ensemble_legend_trace, row=1, col=1)

        # Add legend for history trace with legendrank after vectors
        if self._added_history_trace:
            history_legend_trace = {
                "name": "History",
                "x": [None],
                "y": [None],
                "legendgroup": "History",
                "showlegend": True,
                "visible": True,
                "mode": "lines",
                "line": {
                    "color": self._history_vector_color,
                },
                "legendrank": len(self._added_ensemble_traces) + 1,
            }
            self._figure.add_trace(
                trace=history_legend_trace,
                row=1,
                col=1,
            )

        # Add legend for observation trace with legendrank after history vector
        if self._added_observation_trace:
            observation_legend_trace = {
                "name": "Observation",
                "x": [None],
                "y": [None],
                "legendgroup": "Observation",
                "showlegend": True,
                "visible": True,
                "mode": "markers+lines",
                "marker": {"color": self._observation_color},
                "line": {"color": self._observation_color},
                "legendrank": len(self._added_ensemble_traces) + 2,
            }
            self._figure.add_trace(
                trace=observation_legend_trace,
                row=1,
                col=1,
            )

    def add_realizations_traces(
        self,
        vectors_df: pd.DataFrame,
        ensemble: str,
        color_lightness_scale: Optional[float] = None,
    ) -> None:
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        if color_lightness_scale:
            # Range: 50% - 150% lightness
            scale = max(50.0, min(150.0, color_lightness_scale))
            color = rgb_to_str(scale_rgb_lightness(hex_to_rgb(color), scale))

        # Get vectors - order not important
        vectors: Set[str] = set(vectors_df.columns) - set(["DATE", "REAL"])
        self._validate_vectors_are_selected(vectors)

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}

        for vector in vectors:
            line_shape = self._vector_line_shapes.get(vector, self._line_shape_fallback)
            vector_traces_set[vector] = create_vector_realization_traces(
                vector_df=vectors_df[["DATE", "REAL", vector]],
                ensemble=ensemble,
                legend_group=ensemble,
                color=color,
                line_shape=line_shape,
                hovertemplate=render_hovertemplate(vector, self._sampling_frequency),
            )

        # If vector data is added for ensemble
        if vector_traces_set:
            self._update_added_ensemble_traces_list(ensemble)

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_statistics_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        statistics_options: List[StatisticsOptions],
        line_width: Optional[int] = None,
        color_lightness_scale: Optional[float] = None,
    ) -> None:
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        if color_lightness_scale:
            # Range: 50% - 150% lightness
            scale = max(50.0, min(150.0, color_lightness_scale))
            color = rgb_to_str(scale_rgb_lightness(hex_to_rgb(color), scale))

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}

        # Get vectors - order not important
        vectors: Set[str] = set(
            vectors_statistics_df.columns.get_level_values(0)
        ) - set(["DATE"])
        self._validate_vectors_are_selected(vectors)

        for vector in vectors:
            # Retrieve DATE and statistics columns for specific vector
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            line_shape = self._vector_line_shapes.get(vector, self._line_shape_fallback)
            vector_traces_set[vector] = create_vector_statistics_traces(
                vector_statistics_df=vector_statistics_df,
                color=color,
                legend_group=ensemble,
                line_shape=line_shape,
                line_width=line_width if line_width else 2,
                hovertemplate=render_hovertemplate(vector, self._sampling_frequency),
                statistics_options=statistics_options,
            )

        # If vector data is added for ensemble
        if vector_traces_set:
            self._update_added_ensemble_traces_list(ensemble)

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_fanchart_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        fanchart_options: List[FanchartOptions],
    ) -> None:
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}

        # Get vectors - order not important
        vectors: Set[str] = set(
            vectors_statistics_df.columns.get_level_values(0)
        ) - set(["DATE"])
        self._validate_vectors_are_selected(vectors)

        for vector in vectors:
            # Retrieve DATE and statistics columns for specific vector
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            line_shape = self._vector_line_shapes.get(vector, self._line_shape_fallback)
            vector_traces_set[vector] = create_vector_fanchart_traces(
                vector_statistics_df=vector_statistics_df,
                hex_color=color,
                legend_group=ensemble,
                line_shape=line_shape,
                fanchart_options=fanchart_options,
                hovertemplate=render_hovertemplate(vector, self._sampling_frequency),
            )

        # If vector data is added for ensemble
        if vector_traces_set:
            self._update_added_ensemble_traces_list(ensemble)

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_history_traces(
        self,
        vectors_df: pd.DataFrame,
        __ensemble: Optional[str] = None,
    ) -> None:
        # NOTE: Not using ensemble argument for this implementation!

        if "DATE" not in vectors_df.columns and "REAL" not in vectors_df.columns:
            raise ValueError('vectors_df is missing required columns ["DATE","REAL"]')

        # Get vectors - order not important
        vectors: Set[str] = set(vectors_df.columns) - set(["DATE", "REAL"])
        self._validate_vectors_are_selected(vectors)

        samples = vectors_df["DATE"].tolist()

        vector_trace_set: Dict[str, dict] = {}
        for vector in vectors:
            # Set status for added history trace
            self._added_history_trace = True

            line_shape = self._vector_line_shapes.get(vector, self._line_shape_fallback)
            vector_trace_set[vector] = create_history_vector_trace(
                samples,
                vectors_df[vector].values,
                line_shape=line_shape,
            )

        self._add_vector_trace_set_to_figure(vector_trace_set)

    def add_vector_observations(
        self, vector_name: str, vector_observations: dict
    ) -> None:
        if vector_name not in self._selected_vectors:
            raise ValueError(f"Vector {vector_name} not among selected vectors!")

        # Set added flag
        self._added_observation_trace = True

        self._add_vector_traces_set_to_figure(
            {
                vector_name: create_vector_observation_traces(
                    vector_observations, color=self._observation_color
                )
            }
        )

    #############################################################################
    #
    # Private methods
    #
    #############################################################################

    def _set_keep_uirevision(self) -> None:
        # Keep uirevision (e.g. zoom) for unchanged data.
        self._figure.update_xaxes(uirevision="locked")  # Time axis state kept
        for i, vector in enumerate(self._selected_vectors, start=1):
            self._figure.update_yaxes(row=i, col=1, uirevision=vector)

    def _add_vector_trace_set_to_figure(
        self, vector_trace_set: Dict[str, dict], __ensemble: Optional[str] = None
    ) -> None:
        for vector, trace in vector_trace_set.items():
            subplot_index = (
                self._selected_vectors.index(vector) + 1
                if vector in self._selected_vectors
                else None
            )
            if subplot_index is None:
                continue
            self._figure.add_trace(trace, row=subplot_index, col=1)

    def _add_vector_traces_set_to_figure(
        self, vector_traces_set: Dict[str, List[dict]], __ensemble: Optional[str] = None
    ) -> None:
        for vector, traces in vector_traces_set.items():
            subplot_index = (
                self._selected_vectors.index(vector) + 1
                if vector in self._selected_vectors
                else None
            )
            if subplot_index is None:
                continue
            self._figure.add_traces(traces, rows=subplot_index, cols=1)

    def _update_added_ensemble_traces_list(self, ensemble: str) -> None:
        """Update added ensemble traces list, to prevent duplicates in list"""
        if ensemble not in self._added_ensemble_traces:
            self._added_ensemble_traces.append(ensemble)

    def _validate_vectors_are_selected(self, vectors: Set[str]) -> None:
        """Validate set of vectors are among selected vectors

        Check if vectors are among selected vectors for figure builder, raise
        ValueError if not.

        `Input:`
        * vectors: Set[str] - set of vector names to verify
        """
        for vector in vectors:
            if vector not in self._selected_vectors:
                raise ValueError(
                    f'Vector "{vector}" does not exist among selected vectors: '
                    f"{self._selected_vectors}"
                )
