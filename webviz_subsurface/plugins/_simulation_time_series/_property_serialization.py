from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

from webviz_config._theme_class import WebvizConfigTheme

from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    Frequency,
)

from .utils.from_timeseries_cumulatives import is_interval_or_average_vector

from ..._utils.fanchart_plotting import (
    get_fanchart_traces,
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
)
from ..._utils.statistics_plotting import (
    create_statistics_traces,
    StatisticsData,
    LineData,
)

from .types import FanchartOptions, StatisticsOptions


class GraphFigureBuilder:
    """
    Figure builder for creating/building serializable Output property data
    for the callback. Where vector traces are added per ensemble.

    Contains functions for adding titles, graph data and retreving the serialized
    data for callback Output property.
    """

    def __init__(
        self,
        selected_vectors: List[str],
        vector_titles: Dict[str, str],
        ensemble_colors: dict,
        sampling_frequency: Optional[Frequency],
        theme: Optional[WebvizConfigTheme] = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        self._selected_vectors = selected_vectors
        self._ensemble_colors = ensemble_colors
        self._sampling_frequency = sampling_frequency
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

    # ------------------------------------
    #
    # Public functions
    #
    # ------------------------------------

    def get_serialized_figure(self) -> dict:
        """
        Get figure on a JSON serialized format - i.e. a dictionary
        """
        return self._figure.to_dict()

    def add_realizations_traces(
        self,
        vectors_df: pd.DataFrame,
        ensemble: str,
        vector_line_shapes: Dict[str, str],
        add_legend: bool = True,
    ) -> None:
        """Add realization traces to figure

        `Input:`
        * vectors_df: pd.Dataframe - Dataframe with columns:
            ["DATE", "REAL", vector1, ..., vectorN]

        """
        color = self._ensemble_colors.get(ensemble)
        if not color:
            raise ValueError(f'Ensemble "{ensemble}" is not present in colors dict!')

        # Dictionary with vector name as key and list of ensemble traces as value
        vector_traces_set: Dict[str, List[dict]] = {}
        vectors: List[str] = list(set(vectors_df.columns) ^ set(["DATE", "REAL"]))

        for vector in set(vectors):
            vector_traces_set[vector] = self._create_vector_realization_traces(
                vector_df=vectors_df[["DATE", "REAL", vector]],
                ensemble=ensemble,
                color=color,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                hovertemplate=self._render_hovertemplate(
                    vector, self._sampling_frequency
                ),
                show_legend=False,
            )

        # Add legend for ensemble - utilize one trace dict
        if add_legend:
            for traces in vector_traces_set.values():
                if len(traces) > 0:
                    trace: dict = traces[0]
                    trace["showlegend"] = add_legend
                    break

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_statistics_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        statistics_options: List[StatisticsOptions],
        vector_line_shapes: Dict[str, str],
        add_legend: bool = True,
    ) -> None:
        """Add statistics traces to figure

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with double column level:\n
          [ "DATE",    vector1,                        ... vectorN
                       MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]

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
            # Retrieve DATE and statistics columns for specific vector
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            vector_traces_set[vector] = self._create_vector_statistics_traces(
                vector_statistics_df=vector_statistics_df,
                color=color,
                legend_group=ensemble,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                hovertemplate=self._render_hovertemplate(
                    vector=vector, sampling_frequency=self._sampling_frequency
                ),
                statistics_options=statistics_options,
                show_legend=False,
            )

        # Set show legend on last trace in last vector trace list (mean will be last
        # trace with solid line)
        if (
            add_legend
            and len(vector_traces_set) > 0
            and len(list(vector_traces_set.values())[-1]) > 0
        ):
            trace = list(vector_traces_set.values())[-1][-1]
            trace["showlegend"] = add_legend

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_fanchart_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        fanchart_options: List[FanchartOptions],
        vector_line_shapes: Dict[str, str],
        add_legend: bool = True,
    ) -> None:
        """
        Add fanchart traces for vectors in provided vectors statistics dataframe

        `Input:`
        * Dataframe with double column level:\n
          [ "DATE",    vector1,                        ... vectorN
                       MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]
        """
        # TODO: Add verification of format and raise value error - i.e required columns and
        # "dimension" of vectors_statistics_df

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
            # Retrieve DATE and statistics columns for specific vector
            vector_statistics_df = pd.DataFrame(vectors_statistics_df["DATE"]).join(
                vectors_statistics_df[vector]
            )
            vector_traces_set[vector] = self._create_vector_fanchart_traces(
                vector_statistics_df=vector_statistics_df,
                color=color,
                legend_group=ensemble,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
                fanchart_options=fanchart_options,
                show_legend=False,
                hovertemplate=self._render_hovertemplate(
                    vector=vector, sampling_frequency=self._sampling_frequency
                ),
            )

        # Set show legend on last trace in last vector trace list (mean will be last
        # trace with solid line)
        if (
            add_legend
            and len(vector_traces_set) > 0
            and len(list(vector_traces_set.values())[-1]) > 0
        ):
            trace = list(vector_traces_set.values())[-1][-1]
            trace["showlegend"] = add_legend

        # Add traces to figure
        self._add_vector_traces_set_to_figure(vector_traces_set)

    def add_history_traces(
        self,
        vectors_df: pd.DataFrame,
        vector_line_shapes: Dict[str, str],
        add_legend: bool = True,
    ) -> None:
        """Add traces for historical vectors in dataframe columns

        `Input:`
        * vectors_df - dataframe with non-historical vector names in columns and their
        historical data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]
        """
        # TODO: Add verification of format and raise value error - i.e required columns and
        # "dimension" of vectors_df
        if "DATE" not in vectors_df.columns and "REAL" not in vectors_df.columns:
            raise ValueError('vectors_df is missing required columns ["DATE","REAL"]')

        vector_names = [
            col for col in vectors_df.columns if col not in ["DATE", "REAL"]
        ]

        samples = vectors_df["DATE"].tolist()

        vector_trace_set: Dict[str, dict] = {}
        for vector in vector_names:
            vector_trace_set[vector] = self._create_history_vector_trace(
                samples,
                vectors_df[vector].values,
                line_shape=vector_line_shapes.get(vector, self._line_shape_fallback),
            )

        if add_legend and len(vector_trace_set) > 0:
            trace = list(vector_trace_set.values())[0]
            trace["showlegend"] = add_legend
        self._add_vector_trace_set_to_figure(vector_trace_set)

    def add_vector_observations(
        self, vector_name: str, vector_observations: dict
    ) -> None:
        if vector_name not in self._selected_vectors:
            raise ValueError(f"Vector {vector_name} not among selected vectors!")

        observation_traces: List[dict] = []
        for observation in vector_observations.get("observations", []):
            observation_traces.append(
                {
                    "x": [observation.get("date"), []],
                    "y": [observation.get("value"), []],
                    "marker": {"color": "black"},
                    "text": observation.get("comment", None),
                    "hoverinfo": "y+x+text",
                    "showlegend": False,
                    "error_y": {
                        "type": "data",
                        "array": [observation.get("error"), []],
                        "visible": True,
                    },
                }
            )
        vector_observations_traces_set = {vector_name: observation_traces}
        self._add_vector_traces_set_to_figure(vector_observations_traces_set)

    # ------------------------------------
    #
    # Private functions
    #
    # ------------------------------------

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

    @staticmethod
    def _create_vector_realization_traces(
        vector_df: pd.DataFrame,
        ensemble: str,
        color: str,
        line_shape: str,
        hovertemplate: str,
        show_legend: bool = True,
    ) -> List[dict]:
        """Renders line trace for each realization, includes history line if present

        `Input:`
        * vector_df: pd.DataFrame - Dataframe with vector data with following columns:\n
        ["DATE", "REAL", vector]
        * ensemble: str - Name of ensemble
        """
        vector_names = list(set(vector_df.columns) ^ set(["DATE", "REAL"]))
        if len(vector_names) != 1:
            raise ValueError(
                f"Expected one vector column present in dataframe, got {len(vector_names)}!"
            )

        vector_name = vector_names[0]
        return [
            {
                "line": {"shape": line_shape},
                "x": list(real_df["DATE"]),
                "y": list(real_df[vector_name]),
                "hovertemplate": f"{hovertemplate}Realization: {real}, Ensemble: {ensemble}",
                "name": ensemble,
                "legendgroup": ensemble,
                "marker": {"color": color},
                "showlegend": real_no == 0 and show_legend,
            }
            for real_no, (real, real_df) in enumerate(vector_df.groupby("REAL"))
        ]

    @staticmethod
    def _validate_vector_statistics_df_columns(
        vector_statistics_df: pd.DataFrame,
    ) -> None:
        """Validate columns of vector statistics DataFrame

        Verify DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

        Raise value error if columns are not matching

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with dates and vector statistics columns.
        """
        expected_columns = [
            "DATE",
            StatisticsOptions.MEAN,
            StatisticsOptions.MIN,
            StatisticsOptions.MAX,
            StatisticsOptions.P10,
            StatisticsOptions.P90,
            StatisticsOptions.P50,
        ]
        if list(vector_statistics_df.columns) != expected_columns:
            raise ValueError(
                f"Incorrect dataframe columns, expected {expected_columns}, got "
                f"{vector_statistics_df.columns}"
            )

    @staticmethod
    def _create_vector_statistics_traces(
        vector_statistics_df: pd.DataFrame,
        statistics_options: List[StatisticsOptions],
        color: str,
        legend_group: str,
        line_shape: str,
        hovertemplate: str = "(%{x}, %{y})<br>",
        show_legend: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get statistical lines for provided vector statistics DataFrame.

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with dates and vector statistics columns.
          DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

        * statistics_options: List[StatisticsOptions] - List of statistic options to include
        """
        # Validate columns format
        GraphFigureBuilder._validate_vector_statistics_df_columns(vector_statistics_df)

        low_data = (
            LineData(
                data=vector_statistics_df[StatisticsOptions.P90].values,
                name=StatisticsOptions.P90.value,
            )
            if StatisticsOptions.P90 in statistics_options
            else None
        )
        mid_data = (
            LineData(
                data=vector_statistics_df[StatisticsOptions.P50].values,
                name=StatisticsOptions.P50.value,
            )
            if StatisticsOptions.P50 in statistics_options
            else None
        )
        high_data = (
            LineData(
                data=vector_statistics_df[StatisticsOptions.P10].values,
                name=StatisticsOptions.P10.value,
            )
            if StatisticsOptions.P10 in statistics_options
            else None
        )
        mean_data = (
            LineData(
                data=vector_statistics_df[StatisticsOptions.MEAN].values,
                name=StatisticsOptions.MEAN.value,
            )
            if StatisticsOptions.MEAN in statistics_options
            else None
        )
        minimum = (
            vector_statistics_df[StatisticsOptions.MIN].values
            if StatisticsOptions.MIN in statistics_options
            else None
        )
        maximum = (
            vector_statistics_df[StatisticsOptions.MAX].values
            if StatisticsOptions.MAX in statistics_options
            else None
        )

        data = StatisticsData(
            samples=vector_statistics_df["DATE"].values,
            free_line=mean_data,
            minimum=minimum,
            maximum=maximum,
            low=low_data,
            mid=mid_data,
            high=high_data,
        )
        return create_statistics_traces(
            data=data,
            color=color,
            legend_group=legend_group,
            line_shape=line_shape,
            show_legend=show_legend,
            hovertemplate=hovertemplate,
        )

    @staticmethod
    def _create_vector_fanchart_traces(
        vector_statistics_df: pd.DataFrame,
        color: str,
        legend_group: str,
        line_shape: str,
        fanchart_options: List[FanchartOptions],
        show_legend: bool = True,
        hovertemplate: str = "(%{x}, %{y})<br>",
    ) -> List[Dict[str, Any]]:
        """Get statistical fanchart traces for provided vector statistics DataFrame.

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with dates and vector statistics columns.
          DataFrame columns: ["DATE", MEAN, MIN, MAX, P10, P90, P50]

        * statistics_options: List[StatisticsOptions] - List of statistic options to include
        """
        # Validate columns format
        GraphFigureBuilder._validate_vector_statistics_df_columns(vector_statistics_df)

        low_high_data = (
            LowHighData(
                low_data=vector_statistics_df[StatisticsOptions.P90].values,
                low_name="P90",
                high_data=vector_statistics_df[StatisticsOptions.P10].values,
                high_name="P10",
            )
            if FanchartOptions.P10_P90 in fanchart_options
            else None
        )
        minimum_maximum_data = (
            MinMaxData(
                minimum=vector_statistics_df[StatisticsOptions.MIN].values,
                maximum=vector_statistics_df[StatisticsOptions.MAX].values,
            )
            if FanchartOptions.MIN_MAX in fanchart_options
            else None
        )
        mean_data = (
            FreeLineData(
                "Mean",
                vector_statistics_df[StatisticsOptions.MEAN].values,
            )
            if FanchartOptions.MEAN in fanchart_options
            else None
        )

        data = FanchartData(
            samples=vector_statistics_df["DATE"].tolist(),
            low_high=low_high_data,
            minimum_maximum=minimum_maximum_data,
            free_line=mean_data,
        )
        return get_fanchart_traces(
            data=data,
            color=color,
            legend_group=legend_group,
            line_shape=line_shape,
            show_legend=show_legend,
            hovertemplate=hovertemplate,
        )

    @staticmethod
    def _create_history_vector_trace(
        samples: list,
        history_data: np.ndarray,
        line_shape: str,
        show_legend: bool = False,
    ) -> dict:
        """Returns the history trace line"""
        if len(samples) != len(history_data):
            raise ValueError("Number of samples unequal number of data points!")

        return {
            "line": {"shape": line_shape},
            "x": samples,
            "y": history_data,
            "hovertext": "History",
            "hoverinfo": "y+x+text",
            "name": "History",
            "marker": {"color": "black"},
            "showlegend": show_legend,
            "legendgroup": "History",
        }

    @staticmethod
    def _render_hovertemplate(
        vector: str, sampling_frequency: Optional[Frequency]
    ) -> str:
        """Based on render_hovertemplate(vector: str, interval: Optional[str]) in
        webviz_subsurface/_utils/simulation_timeseries.py

        Adjusted to use Frequency enum and handle "Raw" and "weekly" frequency.
        """
        if is_interval_or_average_vector(vector) and sampling_frequency:
            if sampling_frequency in [Frequency.DAILY, Frequency.WEEKLY]:
                return "(%{x|%b} %{x|%-d}, %{x|%Y}, %{y})<br>"
            if sampling_frequency == Frequency.MONTHLY:
                return "(%{x|%b} %{x|%Y}, %{y})<br>"
            if sampling_frequency == Frequency.YEARLY:
                return "(%{x|%Y}, %{y})<br>"
            raise ValueError(f"Interval {sampling_frequency.value} is not supported.")
        return "(%{x}, %{y})<br>"  # Plotly's default behavior
