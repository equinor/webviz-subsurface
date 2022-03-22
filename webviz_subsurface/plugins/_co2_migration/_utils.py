from typing import Optional
from enum import Enum


FAULT_POLYGON_ATTRIBUTE = "dl_extracted_faultlines"


class MapAttribute(Enum):
    MigrationTime = "migration-time"
    MaxSaturation = "max-saturation"
