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


class CorrType(StrEnum):
    SIM_VS_PARAM = "sim_vs_param"
    PARAM_VS_SIM = "param_vs_sim"
