from webviz_subsurface._utils.enum_shim import StrEnum


class PROPERTYTYPE(StrEnum):
    STATIC = "Static"
    DYNAMIC = "Dynamic"


class GRIDDIRECTION(StrEnum):
    I = "I"
    J = "J"
    K = "K"
