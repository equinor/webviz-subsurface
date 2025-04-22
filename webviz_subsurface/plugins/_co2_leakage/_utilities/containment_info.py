from dataclasses import dataclass
from typing import List, Optional

from webviz_subsurface._utils.enum_shim import StrEnum


class StatisticsTabOption(StrEnum):
    PROBABILITY_PLOT = "probability-plot"
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
    use_stats: bool
    date_option: str
    statistics_tab_option: StatisticsTabOption
    box_show_points: str
