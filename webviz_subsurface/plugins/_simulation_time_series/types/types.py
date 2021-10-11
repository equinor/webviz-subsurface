from enum import Enum

# TODO: Move to main_view.py? Perhaps not if view should not depend on data,
# but only fill based on initial callback?
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

    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    P10 = "p10"
    P90 = "p90"
    P50 = "p50"


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
