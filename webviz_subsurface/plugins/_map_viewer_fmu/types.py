from dataclasses import dataclass
from typing import List, Optional


@dataclass
class WellsContext:
    well_names: List[str]


@dataclass
class SurfaceContext:
    ensemble: str
    realizations: List[int]
    attribute: str
    date: Optional[str]
    name: str
    mode: str


@dataclass
class LogContext:
    """Contains the log name for a given well and logrun"""

    well: str
    log: str
    logrun: str
