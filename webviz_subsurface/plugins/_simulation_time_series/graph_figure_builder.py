from typing import Dict, List, Optional, TypedDict

import pandas as pd
from plotly.subplots import make_subplots

from webviz_config._theme_class import WebvizConfigTheme

from .utils.plotting import (
    create_vector_fanchart_traces,
    create_vector_history_trace,
    create_vector_realization_traces,
    create_vector_statistics_traces,
)

from ..._utils.simulation_timeseries import (
    render_hovertemplate,
)

from .types import FanchartOptions, StatisticsOptions


class VectorLineShape(TypedDict):
    vector: str
    line_shape: str


class GraphFigureBuilder:
    """
    Building graph figure, where respective vector traces are added per ensemble
    """

    def __init__(
        self,
        selected_vectors: List[str],
        vector_titles: Dict[str, str],
        ensemble_colors: dict,
        sampling: str,
        theme: Optional[WebvizConfigTheme] = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        self._selected_vectors = selected_vectors
        self._ensemble_colors = ensemble_colors
        self._sampling = sampling
        self._figure = make_subplots(
            rows=max(1, len(self._selected_vectors)),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[vector_titles.get(elm, elm) for elm in selected_vectors],
        )
        if theme:
            self._figure.update_layout(
                theme.create_themed_layout(self._figure.to_dict().get("layout", {}))
            )
        self._set_keep_uirevision()
        self._line_shape_fallback = line_shape_fallback
        self._vector_line_shapes = None

    def _set_keep_uirevision(self) -> None:
        # Keep uirevision (e.g. zoom) for unchanged data.
        self._figure.update_xaxes(uirevision="locked")  # Time axis state kept
        for i, vector in enumerate(self._selected_vectors, start=1):
            self._figure.update_yaxes(row=i, col=1, uirevision=vector)

    def _add_vector_traces_set_to_figure(
        self, vector_traces_set: Dict[str, List[dict]]
    ) -> None:
        """
        Add list of vector line traces to figure.

        Places line traces for specified vector into correc subplot of figure

        `Input:`
        * vector_traces_set: Dict[str, List[dict]] - Dictionary with vector names and list
        of vector line traces for figure.

        """
        for vector, traces in vector_traces_set.items():
            subplot_index = (
                self._selected_vectors.index(vector) + 1
                if vector in self._selected_vectors
                else None
            )
            if subplot_index is None:
                continue
            self._figure.add_traces(traces, rows=subplot_index, cols=1)

    def _add_vector_trace_set_to_figure(
        self, vector_trace_set: Dict[str, dict]
    ) -> None:
        """
        Add vector line trace to figure

        Places line trace for specified vector into correc subplot of figure

        `Input:`
        * vector_traces_set: Dict[str, dict] - Dictionary with vector name and single
        vector line trace for figure.
        """
        for vector, trace in vector_trace_set.items():
            subplot_index = (
                self._selected_vectors.index(vector) + 1
                if vector in self._selected_vectors
                else None
            )
            if subplot_index is None:
                continue
            self._figure.add_trace(trace, row=subplot_index, col=1)

    def add_realizations_traces(
        self,
        vectors_df: pd.DataFrame,
        ensemble: str,
        vector_line_shapes: Dict[str, str],
    ) -> None:
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}
        vectors = [
            col for col in vectors_df.columns.tolist() if col not in ["DATE", "REAL"]
        ]

        for vector in set(vectors):
            vector_traces_set[vector] = create_vector_realization_traces(
                ensemble_vectors_df=vectors_df,
                vector=vector,
                ensemble=ensemble,
                color=color,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                hovertemplate=render_hovertemplate(vector, self._sampling),
                show_legend=False,
            )

        # Add legend for ensemble - utilize one trace dict
        for traces in vector_traces_set.values():
            if len(traces) > 0:
                trace: dict = traces[0]
                trace["showlegend"] = True
                break

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_statistics_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        statistics_options: List[StatisticsOptions],
        vector_line_shapes: Dict[str, str],
    ) -> None:
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}

        vector_names = {
            name
            for name in set(vectors_statistics_df.columns.get_level_values(0))
            if name != "DATE"
        }
        for vector in set(vector_names):
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            vector_traces_set[vector] = create_vector_statistics_traces(
                vector_statistics_df=vector_statistics_df,
                color=color,
                legend_group=ensemble,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                hovertemplate=render_hovertemplate(
                    vector=vector, interval=self._sampling
                ),
                statistics_options=statistics_options,
                show_legend=False,
            )

        # Add legend for ensemble - utilize one trace dict
        for traces in vector_traces_set.values():
            if len(traces) > 0:
                trace: dict = traces[0]
                trace["showlegend"] = True
                break

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_fanchart_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        fanchart_options: List[FanchartOptions],
        vector_line_shapes: Dict[str, str],
    ) -> None:
        """
        Add fanchart traces for vectors in provided vectors statistics dataframe

        `Input:`
        * Dataframe with double column level:\n
          [            vector1,                        ... vectorN
            "DATE",    mean, min, max, p10, p90, p50   ... mean, min, max, p10, p90, p50]
        """
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}
        vector_names = {
            name
            for name in set(vectors_statistics_df.columns.get_level_values(0))
            if name != "DATE"
        }

        for vector in set(vector_names):
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            vector_traces_set[vector] = create_vector_fanchart_traces(
                vector_statistics_df=vector_statistics_df,
                color=color,
                legend_group=ensemble,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                fanchart_options=fanchart_options,
                show_legend=False,
                hovertemplate=render_hovertemplate(
                    vector=vector, interval=self._sampling
                ),
            )

        # Set show legend on last trace in last vector trace list (mean will be last
        # trace with solid line)
        if len(vector_traces_set) > 0 and len(list(vector_traces_set.values())[-1]) > 0:
            trace = list(vector_traces_set.values())[-1][-1]
            trace["showlegend"] = True

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_history_traces(
        self, vectors_df: pd.DataFrame, vector_line_shapes: Dict[str, str]
    ) -> None:
        """Add traces for historical vectors in dataframe columns

        `Input:`
        * vectors_df - dataframe with non-historical vector names in columns and their
        historical data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]
        """

        vector_names = [
            col for col in vectors_df.columns if col not in ["DATE", "REAL"]
        ]

        samples = vectors_df["DATE"].tolist()

        vector_trace_set: Dict[str, dict] = {}
        for vector in vector_names:
            vector_trace_set[vector] = create_vector_history_trace(
                samples,
                vectors_df[vector].values,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
            )

        if len(vector_trace_set) > 0:
            trace = list(vector_trace_set.values())[0]
            trace["showlegend"] = True
        self._add_vector_trace_set_to_figure(vector_trace_set)

    def get_figure(self) -> dict:
        return self._figure.to_dict()
