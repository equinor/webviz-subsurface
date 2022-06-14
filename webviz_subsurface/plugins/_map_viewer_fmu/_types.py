from enum import Enum


class LayerTypes(str, Enum):
    HILLSHADING = "Hillshading2DLayer"
    MAP3D = "Map3DLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"
    WELLTOPSLAYER = "GeoJsonLayer"
    DRAWING = "DrawingLayer"
    FAULTPOLYGONS = "FaultPolygonsLayer"
    GEOJSON = "GeoJsonLayer"


class LayerNames(str, Enum):
    HILLSHADING = "Surface (hillshading)"
    MAP3D = "3D Map"
    COLORMAP = "Surface (color)"
    WELL = "Wells"
    WELLTOPSLAYER = "Well tops"
    DRAWING = "Drawings"
    FAULTPOLYGONS = "Fault polygons"
    GEOJSON = "GeoJsonLayer"


class SurfaceMode(str, Enum):
    MEAN = "Mean"
    REALIZATION = "Single realization"
    OBSERVED = "Observed"
    STDDEV = "StdDev"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"
