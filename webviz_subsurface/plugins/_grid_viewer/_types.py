from enum import Enum


class PROPERTYTYPE(str, Enum):
    STATIC = "Static"
    DYNAMIC = "Dynamic"


class GRID_DIRECTION(str, Enum):
    I = "I"
    J = "J"
    K = "K"
