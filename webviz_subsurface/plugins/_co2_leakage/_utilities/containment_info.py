from dataclasses import dataclass
from enum import StrEnum
from typing import List


class StatisticsTabOption(StrEnum):
    PROBABILITY_PLOT = "probability-plot"
    BOX_PLOT = "box-plot"


@dataclass(slots=True)
class ContainmentInfo:
    zone: str | None
    region: str | None
    zones: List[str]
    regions: List[str]
    phase: str | None
    containment: str | None
    plume_group: str | None
    color_choice: str
    mark_choice: str | None
    sorting: str
    phases: List[str]
    containments: List[str]
    plume_groups: List[str]
    use_stats: bool
    date_option: str
    statistics_tab_option: StatisticsTabOption
    box_show_points: str
    update_first_figure: bool = False