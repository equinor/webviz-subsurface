from typing import TypedDict

from webviz_config.utils import StrEnum


class DeltaEnsemble(TypedDict):
    """Definition of delta ensemble

    Pair of names representing a delta ensemble: A-B
    """

    ensemble_a: str
    ensemble_b: str


class FanchartOptions(StrEnum):
    """
    Type definition for statistical options for fanchart
    """

    MEAN = "Mean"  # Mean value
    MIN_MAX = "Min/Max"  # Minimum and maximum pair
    P10_P90 = "P10/P90"  # P10 and P90 pair


class StatisticsFromOptions(StrEnum):
    """
    Type definition of options for what to generate statistics from in simulation time series
    """

    ALL_REALIZATIONS = "all_realizations"
    SELECTED_REALIZATIONS = "selected_realizations"


class StatisticsOptions(StrEnum):
    """
    Type definition of statistics to include in plot in simulation time series
    """

    MEAN = "Mean"
    MIN = "Min"
    MAX = "Max"
    P10 = "P10"
    P90 = "P90"
    P50 = "P50"


class SubplotGroupByOptions(StrEnum):
    """
    Type definition of options for subplots "group by" in graph for simulation time series
    """

    VECTOR = "vector"
    ENSEMBLE = "ensemble"


class TraceOptions(StrEnum):
    """
    Type definition for trace options in simulation time series
    """

    HISTORY = "history"
    OBSERVATIONS = "observations"


class VisualizationOptions(StrEnum):
    """
    Type definition for visualization options in simulation time series
    """

    REALIZATIONS = "realizations"
    STATISTICS = "statistics"
    FANCHART = "fanchart"
    STATISTICS_AND_REALIZATIONS = "statistics and realizations"
