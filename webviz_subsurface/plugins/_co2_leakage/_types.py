from typing import TypedDict, Optional, List


class LegendData(TypedDict):
    bar_legendonly: Optional[List[str]]
    time_legendonly: Optional[List[str]]
    stats_legendonly: Optional[List[str]]
    box_legendonly: Optional[List[str]]
