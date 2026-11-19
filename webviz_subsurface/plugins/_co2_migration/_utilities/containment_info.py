from dataclasses import dataclass
from typing import List, Optional

from webviz_subsurface._utils.enum_shim import StrEnum


class MainTabOption(StrEnum):
    CONTAINMENT_STATE = "containment-state"
    CONTAINMENT_OVER_TIME = "containment-over-time"
    PROBABILITY = "probability"
    BOX_PLOT = "box-plot"


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)  # NBNB-AS: Removed slots=True (python>=3.10)
class ContainmentInfo:
    zone: Optional[str]
    region: Optional[str]
    zones: List[str]
    regions: Optional[List[str]]
    phase: Optional[str]
    containment: Optional[str]
    plume_group: Optional[str]
    color_choice: str
    mark_choice: str
    sorting: str
    phases: List[str]
    containments: List[str]
    plume_groups: List[str]
    show_realizations: bool
    date_option: str
    points_to_show: str
