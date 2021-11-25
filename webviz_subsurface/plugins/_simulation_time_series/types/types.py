import sys
from enum import Enum

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class DeltaEnsemble(TypedDict):
    """Definition of delta ensemble

    Pair of names representing a delta ensemble: A-B
    """

    ensemble_a: str
    ensemble_b: str


class FanchartOptions(str, Enum):
    """
    Type definition for statistical options for fanchart
    """

    MEAN = "Mean"  # Mean value
    MIN_MAX = "Min/Max"  # Minimum and maximum pair
    P10_P90 = "P10/P90"  # P10 and P90 pair


class StatisticsOptions(str, Enum):
    """
    Type definition for statistics options in simulation time series
    """

    MEAN = "Mean"
    MIN = "Min"
    MAX = "Max"
    P10 = "P10"
    P90 = "P90"
    P50 = "P50"


class TraceOptions(str, Enum):
    """
    Type definition for trace options in simulation time series
    """

    HISTORY = "history"


class VisualizationOptions(str, Enum):
    """
    Type definition for visualization options in simulation time series
    """

    REALIZATIONS = "realizations"
    STATISTICS = "statistics"
    FANCHART = "fanchart"
