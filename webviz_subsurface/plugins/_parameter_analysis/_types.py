from webviz_config.utils import StrEnum


class VisualizationType(StrEnum):
    HISTOGRAM = "histogram"
    DISTRIBUTION = "distribution"
    BOX = "box"
    STAT_TABLE = "stat-table"


class LinePlotOptions(StrEnum):
    """
    Type definition for visualization options in simulation time series
    """

    REALIZATIONS = "realizations"
    STATISTICS = "statistics"
    STATISTICS_AND_REALIZATIONS = "statistics and realizations"
