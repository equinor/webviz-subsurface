from webviz_config.utils import StrEnum


class PressurePlotMode(StrEnum):
    MEAN = "mean"
    SINGLE_REAL = "single-real"


class NodeType(StrEnum):
    WELL = "well"
    GROUP = "group"
    WELL_BH = "well-bh"


class ChartType(StrEnum):
    BAR = "bar"
    PIE = "pie"
    AREA = "area"


class StatType(StrEnum):
    MEAN = "mean"
    P10 = "p10"
    P50 = "p50"
    P90 = "p90"
    MAX = "max"
    MIN = "min"
    P10_MINUS_P90 = "p10-p90"
