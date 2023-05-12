from webviz_config.utils import StrEnum


class LineType(StrEnum):
    REALIZATION = "realization"
    MEAN = "mean"


class ScaleType(StrEnum):
    PERCENTAGE = "Percentage"
    ABSOLUTE = "Absolute"
    TRUE_VALUE = "True"


class LabelOptions(StrEnum):
    DETAILED = "detailed"
    SIMPLE = "simple"
    HIDE = "hide"
