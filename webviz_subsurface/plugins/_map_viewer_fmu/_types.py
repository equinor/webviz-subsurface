from webviz_subsurface._utils.enum_shim import StrEnum


class LayerTypes(StrEnum):
    HILLSHADING = "Hillshading2DLayer"
    MAP3D = "MapLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"
    WELLTOPSLAYER = "GeoJsonLayer"
    DRAWING = "DrawingLayer"
    FAULTPOLYGONS = "FaultPolygonsLayer"
    FIELD_OUTLINE = "GeoJsonLayer"
    GEOJSON = "GeoJsonLayer"


class LayerNames(StrEnum):
    HILLSHADING = "Surface (hillshading)"
    MAP3D = "3D Map"
    COLORMAP = "Surface (color)"
    WELL = "Wells"
    WELLTOPSLAYER = "Well tops"
    DRAWING = "Drawings"
    FAULTPOLYGONS = "Fault polygons"
    GEOJSON = "GeoJsonLayer"


class SurfaceMode(StrEnum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"
