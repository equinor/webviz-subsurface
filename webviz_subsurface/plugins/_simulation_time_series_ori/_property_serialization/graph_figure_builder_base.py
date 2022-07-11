import abc
from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from ..types import FanchartOptions, StatisticsOptions


class GraphFigureBuilderBase(abc.ABC):
    """
    Base class for creating/building serializable Output property data
    for the callback. Has functionality for creating various plot traces, where
    the class inheriting the base is responsible to retrieve the data and place
    correct in graph figure - e.g. place traces in correct subplots, set correct
    titles, legends and so on.

    Contains interface for adding graph data and retreving the serialized data
    for callback Output property.

    Contains self._figure, an empty FigureWidget to either use or override
    """

    def __init__(self) -> None:
        self._figure = go.Figure()

    # ------------------------------------
    #
    # Public functions
    #
    # ------------------------------------

    def get_serialized_figure(self) -> dict:
        """
        Get the built figure on a JSON serialized format - i.e. a dictionary
        """
        return self._figure.to_dict()

    @abc.abstractmethod
    def create_graph_legends(self) -> None:
        """Create legends for graphs after trace data is added"""

    @abc.abstractmethod
    def add_realizations_traces(
        self,
        vectors_df: pd.DataFrame,
        ensemble: str,
        color_lightness_scale: Optional[float] = None,
    ) -> None:
        """Add realization traces to figure

        `Input:`
        * vectors_df: pd.Dataframe - Dataframe with columns:
            ["DATE", "REAL", vector1, ..., vectorN]

        * ensemble: str - Name of ensemble providing the input vector data
        * color_lightness_scale: float - Color lightness scale percentage, to adjust trace colors
        relative to original trace line color defined. Range 50% - 150%
        """

    @abc.abstractmethod
    def add_statistics_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        statistics_options: List[StatisticsOptions],
        line_width: Optional[int] = None,
        color_lightness_scale: Optional[float] = None,
    ) -> None:
        """Add statistics traces to figure

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with double column level:\n
          [ "DATE",    vector1,                        ... vectorN
                       MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]

        * ensemble: str - Name of ensemble providing the input vector data
        * statistics_options: List[StatisticsOptions] - List of statistics options traces to include
        * line_width: int - Line width for statistics traces
        * color_lightness_scale: float - Color lightness scale percentage, to adjust trace colors
        relative to original trace line color defined. Range 50% - 150%
        """

    @abc.abstractmethod
    def add_fanchart_traces(
        self,
        vectors_statistics_df: pd.DataFrame,
        ensemble: str,
        fanchart_options: List[FanchartOptions],
    ) -> None:
        """
        Add fanchart traces for vectors in provided vectors statistics dataframe

        `Input:`
        * vector_statistics_df: pd.Dataframe - Dataframe with double column level:\n
          [ "DATE",    vector1,                        ... vectorN
                       MEAN, MIN, MAX, P10, P90, P50   ... MEAN, MIN, MAX, P10, P90, P50]

        * ensemble: str - Name of ensemble providing the input vector data
        * fanchart_options: List[StatisticsOptions] - List of fanchart options traces to include
        """

    @abc.abstractmethod
    def add_history_traces(
        self,
        vectors_df: pd.DataFrame,
        ensemble: str,
    ) -> None:
        """Add traces for historical vectors in dataframe columns

        `Input:`
        * vectors_df: pd.Dataframe - Dataframe with non-historical vector names in columns and their
        historical data in rows. With columns:\n
            ["DATE", "REAL", vector1, ..., vectorN]

        * ensemble: str - Name of ensemble providing the input vector data
        """

    @abc.abstractmethod
    def add_vector_observations(
        self, vector_name: str, vector_observations: dict
    ) -> None:
        """Add traces for vector observations

        `Input:`
        * vector_name: str - Vector to add observations for
        * vector_observations: dict - Dictionary with observation data for vector
        """

    # ------------------------------------
    #
    # Private functions
    #
    # ------------------------------------

    @abc.abstractmethod
    def _add_vector_traces_set_to_figure(
        self, vector_traces_set: Dict[str, List[dict]], ensemble: Optional[str] = None
    ) -> None:
        """
        Add list of vector line traces to figure.

        Places line traces for specified vector into correct subplot of figure

        `Input:`
        * vector_traces_set: Dict[str, List[dict]] - Dictionary with vector names and list
        of vector line traces for figure.
        * ensemble: str - Optional name of ensemble providing the input vector data
        """

    @abc.abstractmethod
    def _add_vector_trace_set_to_figure(
        self, vector_trace_set: Dict[str, dict], ensemble: Optional[str] = None
    ) -> None:
        """
        Add vector line trace to figure

        Places line trace for specified vector into correct subplot of figure

        `Input:`
        * vector_trace_set: Dict[str, dict] - Dictionary with vector name and single
        vector line trace for figure.
        * ensemble: str - Optional name of ensemble providing the input vector data
        """
