from typing import List, Optional, TypedDict


class LegendData(TypedDict):
    bar_legendonly: Optional[List[str]]
    time_legendonly: Optional[List[str]]
    stats_legendonly: Optional[List[str]]
