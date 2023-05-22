from webviz_config.utils import StrEnum


class LineType(StrEnum):
    REALIZATION = "realizations"
    STATISTICS = "statistics"


class ScaleType(StrEnum):
    PERCENTAGE = "Percentage"
    ABSOLUTE = "Absolute"
    TRUE_VALUE = "True"


class LabelOptions(StrEnum):
    DETAILED = "detailed"
    SIMPLE = "simple"
    HIDE = "hide"
