from typing import List, Optional, TypedDict


class LegendData(TypedDict):
    bar_legendonly: Optional[List[str]]
    time_legendonly: Optional[List[str]]
    probability_legendonly: Optional[List[str]]
    box_legendonly: Optional[List[str]]
