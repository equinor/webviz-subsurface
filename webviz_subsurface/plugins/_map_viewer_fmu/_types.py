# pylint: skip-file
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


# To be implemented
@dataclass
class ViewSetting:
    ensemble: str
    attribute: str
    name: str
    date: Optional[str]
    mode: str
    realizations: List[int]
    wells: List[str]
    surface_range: List[float]
    colormap: str
    color_range: List[float]
    colormap_keep_range: bool = False
    surf_type: Optional[str] = None

    def __post_init__(self) -> None:
        self.ensemble = self.ensemble[0]
        self.attribute = self.attribute[0]
        self.name = self.name[0]
        self.date = self.date[0] if self.date else None
        self.mode = SurfaceMode(self.mode)
        self.colormap_keep_range = True if self.colormap_keep_range else False


class SurfaceMode(str, Enum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"
