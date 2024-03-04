from enum import Enum

from webviz_config.utils import StrEnum


class MapAttribute(Enum):
    MIGRATION_TIME = "Migration Time"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"
    MASS = "Mass"
    DISSOLVED = "Dissolved mass"
    FREE = "Free mass"


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
    CONTAINMENT_ACTUAL_VOLUME = "Containment Data (volume, actual)"


class LayoutLabels(str, Enum):
    """Text labels used in layout components"""

    SHOW_FAULTPOLYGONS = "Show fault polygons"
    SHOW_CONTAINMENT_POLYGON = "Show containment polygon"
    SHOW_HAZARDOUS_POLYGON = "Show hazardous polygon"
    SHOW_WELLS = "Show wells"
    WELL_FILTER = "Well filter"
    COMMON_SELECTIONS = "Options and global filters"
    FEEDBACK = "User feedback"
    VISUALIZATION_UPDATE = "Update threshold"


# pylint: disable=too-few-public-methods
class LayoutStyle:
    """CSS styling"""

    OPTIONS_BUTTON = {
        "marginBottom": "10px",
        "width": "100%",
        "height": "30px",
        "line-height": "30px",
        "background-color": "lightgrey",
    }

    FEEDBACK_BUTTON = {
        "marginBottom": "10px",
        "width": "100%",
        "height": "30px",
        "line-height": "30px",
        "background-color": "lightgrey",
    }

    VISUALIZATION_BUTTON = {
        "marginLeft": "10px",
        "height": "30px",
        "line-height": "30px",
        "background-color": "lightgrey",
    }


class ContainmentViews(StrEnum):
    CONTAINMENTSPLIT = "Split into containment polygons"
    ZONESPLIT = "Split into zones"
    REGIONSPLIT = "Split into regions"
