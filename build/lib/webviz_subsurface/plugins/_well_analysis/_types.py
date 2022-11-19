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
