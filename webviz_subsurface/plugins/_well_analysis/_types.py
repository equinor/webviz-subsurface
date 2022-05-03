from enum import Enum


class PressurePlotMode(str, Enum):
    MEAN = "mean"
    SINGLE_REAL = "single-real"
