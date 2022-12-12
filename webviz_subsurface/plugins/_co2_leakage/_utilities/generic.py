from enum import Enum

from webviz_config.utils import StrEnum


class MapAttribute(Enum):
    MIGRATION_TIME = "Migration Time"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"


class Co2Scale(StrEnum):
    NORMALIZE = "Fraction"
    MTONS = "M tons"
    KG = "Kg"


class GraphSource(StrEnum):
    UNSMRY = "UNSMRY"
    CONTAINMENT = "Containment Data"
