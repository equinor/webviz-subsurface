from enum import Enum

from webviz_config.utils import StrEnum


class MapAttribute(Enum):
    MIGRATION_TIME = "Migration Time"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"


class Co2MassScale(StrEnum):
    NORMALIZE = "Fraction"
    MTONS = "M tons"
    KG = "Kg"


class Co2VolumeScale(StrEnum):
    NORMALIZE = "Fraction"
    BILLION_CUBIC_METERS = "Cubic kms"
    CUBIC_METERS = "Cubic meters"


class GraphSource(StrEnum):
    UNSMRY = "UNSMRY"
    CONTAINMENT_MASS = "Containment Data (mass)"
    CONTAINMENT_VOLUME_ACTUAL = "Containment Data (volume, actual)"
    CONTAINMENT_VOLUME_ACTUAL_SIMPLE = "Containment Data (volume, actual_simple)"
