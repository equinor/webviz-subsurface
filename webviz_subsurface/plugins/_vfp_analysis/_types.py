from webviz_config.utils import StrEnum


class PressureType(StrEnum):
    BHP = "BHP"
    DP = "DP"


class VfpParam(StrEnum):
    THP = "THP"
    WFR = "WFR"
    GFR = "GFR"
    ALQ = "ALQ"
    RATE = "RATE"
