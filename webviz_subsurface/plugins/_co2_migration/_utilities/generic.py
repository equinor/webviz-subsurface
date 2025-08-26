from __future__ import (  # Change to import Self from typing if we update to Python >3.11
    annotations,
)

from enum import Enum
from typing import Dict, List, TypedDict

from webviz_subsurface._utils.enum_shim import StrEnum


class MapAttribute(StrEnum):
    MIGRATION_TIME_SGAS = "Migration time (SGAS)"
    MIGRATION_TIME_AMFG = "Migration time (AMFG)"
    MIGRATION_TIME_AMFS = "Migration time (AMFS)"
    MIGRATION_TIME_XMFS = "Migration time (XMFS)"
    MIGRATION_TIME_YMFS = "Migration time (YMFS)"
    MIGRATION_TIME_XMF2 = "Migration time (XMF2)"
    MAX_SGAS = "Maximum SGAS"
    MAX_AMFG = "Maximum AMFG"
    MAX_AMFS = "Maximum AMFS"
    MAX_XMFS = "Maximum XMFS"
    MAX_YMFS = "Maximum YMFS"
    MAX_XMF2 = "Maximum XMF2"
    MAX_SGSTRAND = "Maximum SGSTRAND"
    MAX_SGTRH = "Maximum SGTRH"
    SGAS_PLUME = "Plume (SGAS)"
    AMFG_PLUME = "Plume (AMFG)"
    XMF2_PLUME = "Plume (XMF2)"
    SGSTRAND_PLUME = "Plume (SGSTRAND)"
    SGTRH_PLUME = "Plume (SGTRH)"
    MASS = "Mass"
    DISSOLVED_WATER = "Dissolved mass in water phase"
    DISSOLVED_OIL = "Dissolved mass in oil phase"
    FREE = "Free gas mass"
    FREE_GAS = "Free gas phase mass"
    TRAPPED_GAS = "Trapped gas phase mass"
    FREE_3PHASES = "Mixed mass in gas phase"
    FREE_GAS_3PHASES = "Mixed mass in free gas phase"
    TRAPPED_GAS_3PHASES = "Mixed mass in trapped gas phase"


class MapGroup(StrEnum):
    MIGRATION_TIME_SGAS = "SGAS"
    MIGRATION_TIME_AMFG = "AMFG"
    MIGRATION_TIME_AMFS = "AMFS"
    MIGRATION_TIME_XMFS = "XMFS"
    MIGRATION_TIME_YMFS = "YMFS"
    MIGRATION_TIME_XMF2 = "XMF2"
    MAX_SGAS = "SGAS"
    MAX_AMFG = "AMFG"
    MAX_AMFS = "AMFS"
    MAX_XMFS = "XMFS"
    MAX_YMFS = "YMFS"
    MAX_XMF2 = "XMF2"
    MAX_SGSTRAND = "SGSTRAND"
    MAX_SGTRH = "SGTRH"
    SGAS_PLUME = "SGAS"
    AMFG_PLUME = "AMFG"
    XMF2_PLUME = "XMF2"
    SGSTRAND_PLUME = "SGSTRAND"
    SGTRH_PLUME = "SGTRH"
    MASS = "CO2 MASS"
    DISSOLVED_WATER = "CO2 MASS"
    DISSOLVED_OIL = "CO2 MASS"
    FREE = "CO2 MASS"
    FREE_GAS = "CO2 MASS"
    TRAPPED_GAS = "CO2 MASS"
    FREE_3PHASES = "CO2 MASS"
    FREE_GAS_3PHASES = "CO2 MASS"
    TRAPPED_GAS_3PHASES = "CO2 MASS"


map_group_labels = {
    "SGAS": "Gas phase",
    "AMFG": "Dissolved in water phase",
    "AMFS": "Dissolved in water phase",
    "XMFS": "Dissolved in oil phase",
    "YMFS": "Dissolved in gas phase",
    "XMF2": "Dissolved in water phase",
    "SGSTRAND": "Trapped gas phase",
    "SGTRH": "Trapped gas phase",
    "CO2 MASS": "CO2 mass",
}


class MapType(StrEnum):
    MIGRATION_TIME_SGAS = "MIGRATION_TIME"
    MIGRATION_TIME_AMFG = "MIGRATION_TIME"
    MIGRATION_TIME_AMFS = "MIGRATION_TIME"
    MIGRATION_TIME_YMFS = "MIGRATION_TIME"
    MIGRATION_TIME_XMFS = "MIGRATION_TIME"
    MIGRATION_TIME_XMF2 = "MIGRATION_TIME"
    MAX_SGAS = "MAX"
    MAX_AMFG = "MAX"
    MAX_AMFS = "MAX"
    MAX_XMFS = "MAX"
    MAX_YMFS = "MAX"
    MAX_XMF2 = "MAX"
    MAX_SGSTRAND = "MAX"
    MAX_SGTRH = "MAX"
    SGAS_PLUME = "PLUME"
    AMFG_PLUME = "PLUME"
    XMF2_PLUME = "PLUME"
    SGSTRAND_PLUME = "PLUME"
    SGTRH_PLUME = "PLUME"
    MASS = "MASS"
    DISSOLVED_WATER = "MASS"
    DISSOLVED_OIL = "MASS"
    FREE = "MASS"
    FREE_GAS = "MASS"
    TRAPPED_GAS = "MASS"
    FREE_3PHASES = "MASS"
    FREE_GAS_3PHASES = "MASS"
    TRAPPED_GAS_3PHASES = "MASS"


class MapNamingConvention(StrEnum):
    MIGRATION_TIME_SGAS = "migrationtime_sgas"
    MIGRATION_TIME_AMFG = "migrationtime_amfg"
    MIGRATION_TIME_AMFS = "migrationtime_amfs"
    MIGRATION_TIME_XMFS = "migrationtime_xmfs"
    MIGRATION_TIME_YMFS = "migrationtime_ymfs"
    MIGRATION_TIME_XMF2 = "migrationtime_xmf2"
    MAX_SGAS = "max_sgas"
    MAX_AMFG = "max_amfg"
    MAX_AMFS = "max_amfs"
    MAX_XMFS = "max_xmfs"
    MAX_YMFS = "max_ymfs"
    MAX_XMF2 = "max_xmf2"
    MAX_SGSTRAND = "max_sgstrand"
    MAX_SGTRH = "max_sgtrh"
    MASS = "co2_mass_total"
    DISSOLVED_WATER = "co2_mass_dissolved_water_phase"
    DISSOLVED_OIL = "co2_mass_dissolved_oil_phase"
    FREE = "co2_mass_gas_phase"
    FREE_GAS = "co2_mass_free_gas_phase"
    TRAPPED_GAS = "co2_mass_trapped_gas_phase"
    FREE_3PHASES = "co2_mass_gas_phase"
    FREE_GAS_3PHASES = "co2_mass_free_gas_phase"
    TRAPPED_GAS_3PHASES = "co2_mass_trapped_gas_phase"


class PhasesScenario(Enum):
    """
    Which scenario is CO2 amounts calculated in
    """

    TWO_PHASES = 0
    THREE_PHASES = 1


class FilteredMapAttribute:
    def __init__(self, mapping: Dict):
        self.mapping = mapping
        map_types = {
            key: MapType[key].value
            for key in MapAttribute.__members__
            if MapAttribute[key].value in self.mapping
        }
        map_groups = {
            key: MapGroup[key].value
            for key in MapAttribute.__members__
            if MapAttribute[key].value in self.mapping
        }
        map_attrs_with_plume = [
            map_groups[key] for key, value in map_types.items() if value == "MAX"
        ]
        plume_request = {
            f"Plume ({item})": f"{item.lower()}_plume" for item in map_attrs_with_plume
        }
        self.mapping.update(plume_request)
        self.filtered_values = self.filter_map_attribute()

    def filter_map_attribute(self) -> Dict:
        return {
            MapAttribute[key]: self.mapping[MapAttribute[key].value]
            for key in MapAttribute.__members__
            if MapAttribute[key].value in self.mapping
        }

    def __getitem__(self, key: MapAttribute) -> MapAttribute:
        if isinstance(key, MapAttribute):
            return self.filtered_values[key]
        raise KeyError(f"Key must be a MapAttribute, " f"got {type(key)} instead.")

    @property
    def values(self) -> Dict:
        return self.filtered_values


class Co2MassScale(StrEnum):
    NORMALIZE = "Fraction"
    KG = "kg"
    TONS = "tons"
    MTONS = "M tons"


class Co2VolumeScale(StrEnum):
    NORMALIZE = "Fraction"
    BILLION_CUBIC_METERS = "Cubic kms"
    CUBIC_METERS = "Cubic meters"


class GraphSource(StrEnum):
    UNSMRY = "UNSMRY"
    CONTAINMENT_MASS = "Containment Data (mass)"
    CONTAINMENT_ACTUAL_VOLUME = "Containment Data (volume, actual)"


class LayoutLabels(StrEnum):
    """Text labels used in layout components"""

    SHOW_FAULTPOLYGONS = "Show fault polygons"
    SHOW_CONTAINMENT_POLYGON = "Show containment polygon"
    SHOW_HAZARDOUS_POLYGON = "Show hazardous polygon"
    SHOW_WELLS = "Show wells"
    WELL_FILTER = "Well filter"
    COMMON_SELECTIONS = "Options and global filters"
    FEEDBACK = "User feedback"
    VISUALIZATION_UPDATE = "Update threshold"
    VISUALIZATION_THRESHOLDS = "Manage visualization filter"
    ALL_REAL = "Select all"


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

    ALL_REAL_BUTTON = {
        "marginLeft": "10px",
        "height": "25px",
        "line-height": "25px",
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

    THRESHOLDS_BUTTON = {
        "marginTop": "10px",
        "width": "100%",
        "height": "30px",
        "line-height": "30px",
        "padding": "0",
        "background-color": "lightgrey",
    }


class MenuOptions(TypedDict):
    zones: List[str]
    regions: List[str]
    phases: List[str]
    plume_groups: List[str]
    dates: List[str]


class MapThresholds:
    def __init__(self, mapping: FilteredMapAttribute):
        self.standard_thresholds = {
            MapAttribute[key.name].value: 0.0
            for key in mapping.filtered_values.keys()
            if MapType[MapAttribute[key.name].name].value
            not in ["PLUME", "MIGRATION_TIME"]
        }
        if MapAttribute.MAX_AMFG in self.standard_thresholds.keys():
            self.standard_thresholds[MapAttribute.MAX_AMFG] = 0.0005


class BoundarySettings(TypedDict):
    polygon_file_pattern: str
    attribute: str
    hazardous_name: str
    containment_name: str
