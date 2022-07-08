from enum import Enum


# pylint: disable=too-few-public-methods
class TreeModeOptions(str, Enum):
    STATISTICS = "statistics"
    SINGLE_REAL = "single_real"


# pylint: disable=too-few-public-methods
class StatOptions(str, Enum):
    MEAN = "mean"
    P10 = "p10"
    P50 = "p50"
    P90 = "p90"
    MAX = "max"
    MIN = "min"


# pylint: disable=too-few-public-methods
class NodeType(str, Enum):
    PROD = "prod"
    INJ = "inj"
    OTHER = "other"
