from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SurfaceContext:
    ensemble: str
    realizations: List[int]
    attribute: str
    name: str
    date: Optional[str]
    mode: str
