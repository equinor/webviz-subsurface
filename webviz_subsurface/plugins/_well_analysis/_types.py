from enum import Enum


class PressurePlotMode(str, Enum):
    MEAN = "mean"
    SINGLE_REAL = "single-real"


class NodeType(str, Enum):
    WELL = "well"
    GROUP = "group"
    WELL_BH = "well-bh"


class ChartType(str, Enum):
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
