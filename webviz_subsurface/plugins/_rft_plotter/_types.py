from webviz_config.utils import StrEnum


class LineType(StrEnum):
    REALIZATION = "realization"
    FANCHART = "fanchart"


class DepthType(StrEnum):
    TVD = "TVD"
    MD = "MD"


class ColorAndSizeByType(StrEnum):
    MISFIT = "ABSDIFF"
    STDDEV = "STDDEV"
    YEAR = "YEAR"
