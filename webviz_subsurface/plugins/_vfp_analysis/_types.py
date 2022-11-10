from webviz_config.utils import StrEnum


class PressureType(StrEnum):
    BHP = "bhp"
    DP = "dp"


class VfpParam(StrEnum):
    THP = "thp"
    WFR = "wfr"
    GFR = "gfr"
    ALQ = "alq"


# THP types supported
class THPType(StrEnum):
    THP = "THPTYPE.THP"


# Water fraction types for VFPPROD
class WFRType(StrEnum):
    WOR = "WFR.WOR"
    WCT = "WFR.WCT"
    WGR = "WFR.WGR"
    WWR = "WFR.WWR"
    WTF = "WFR.WTF"


# Gas fraction types for VFPPROD
class GFRType(StrEnum):
    GOR = "GFR.GOR"
    GLR = "GFR.GLR"
    OGR = "GFR.OGR"
    MMW = "GFR.MMW"


# Artificial lift types for VFPPROD
class ALQType(StrEnum):
    GRAT = "ALQ.GRAT"
    IGLR = "ALQ.IGLR"
    TGLR = "ALQ.TGLR"
    PUMP = "ALQ.PUMP"
    COMP = "ALQ.COMP"
    DENO = "ALQ.DENO"
    DENG = "ALQ.DENG"
    BEAN = "ALQ.BEAN"
    UNDEFINED = "ALQ.UNDEFINED"
