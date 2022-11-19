from enum import Enum


class PROPERTYTYPE(str, Enum):
    STATIC = "Static"
    DYNAMIC = "Dynamic"


class GRIDDIRECTION(str, Enum):
    I = "I"
    J = "J"
    K = "K"
