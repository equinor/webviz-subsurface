from enum import Enum


class SurfaceMode(Enum):
    REALIZATION = "Single realization"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"
    MEAN = "Mean"
    STDDEV = "StdDev"
