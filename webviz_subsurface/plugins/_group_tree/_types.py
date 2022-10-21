from webviz_config.utils import StrEnum


class TreeModeOptions(StrEnum):
    STATISTICS = "statistics"
    SINGLE_REAL = "single_real"


class StatOptions(StrEnum):
    MEAN = "mean"
    P10 = "p10"
    P50 = "p50"
    P90 = "p90"
    MAX = "max"
    MIN = "min"


class NodeType(StrEnum):
    PROD = "prod"
    INJ = "inj"
    OTHER = "other"


class DataType(StrEnum):
    OILRATE = "oilrate"
    GASRATE = "gasrate"
    WATERRATE = "waterrate"
    WATERINJRATE = "waterinjrate"
    GASINJRATE = "gasinjrate"
    PRESSURE = "pressure"
    BHP = "bhp"
    WMCTL = "wmctl"


class EdgeOrNode(StrEnum):
    EDGE = "edge"
    NODE = "node"
