from typing import TypedDict, Optional, List


class LegendData(TypedDict):
    bar_legendonly: List[str] | None
    time_legendonly: List[str] | None
    stats_legendonly: List[str] | None
