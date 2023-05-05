from webviz_config.utils import StrEnum


class LineType(StrEnum):
    REALIZATION = "realization"
    MEAN = "mean"


class ScaleType(StrEnum):
    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"
    TRUE_VALUE = "true-value"


class LabelOptions(StrEnum):
    DETAILED = "detailed"
    SIMPLE = "simple"
    HIDE = "hide"
