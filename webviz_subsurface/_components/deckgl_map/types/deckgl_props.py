from enum import Enum
from typing import Any, Dict, List, Optional
from geojson.feature import FeatureCollection

import pydeck
from pydeck.types import String
from typing_extensions import Literal


class LayerTypes(str, Enum):
    HILLSHADING = "Hillshading2DLayer"
    MAP3D = "Map3DLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"
    DRAWING = "DrawingLayer"
    FAULTPOLYGONS = "FaultPolygonsLayer"


class LayerIds(str, Enum):
    HILLSHADING = "hillshading-layer"
    MAP3D = "map3d-layer"
    COLORMAP = "colormap-layer"
    WELL = "wells-layer"
    DRAWING = "drawing-layer"
    FAULTPOLYGONS = "fault-polygons-layer"


class LayerNames(str, Enum):
    HILLSHADING = "Hillshading"
    MAP3D = "Map"
    COLORMAP = "Colormap"
    WELL = "Wells"
    DRAWING = "Drawings"
    FAULTPOLYGONS = "Fault polygons"


class DeckGLMapProps:
    """Default prop settings for DeckGLMap"""

    bounds: List[float] = [0, 0, 10000, 10000]
    value_range: List[float] = [0, 1]
    image: str = "/surface/UNDEF.png"
    colormap: str = "/colormaps/viridis_r.png"
    edited_data: Dict[str, Any] = {
        "data": {"type": "FeatureCollection", "features": []},
        "selectedWell": "",
        "selectedFeatureIndexes": [],
    }
    resources: Dict[str, Any] = {}


class WellJsonFormat:
    pass


class Hillshading2DLayer(pydeck.Layer):
    def __init__(
        self,
        image: str = DeckGLMapProps.image,
        name: str = LayerNames.HILLSHADING,
        bounds: List[float] = DeckGLMapProps.bounds,
        value_range: List[float] = [0, 1],
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.HILLSHADING,
            id=uuid if uuid is not None else LayerIds.HILLSHADING,
            image=String(image),
            name=String(name),
            bounds=bounds,
            valueRange=value_range,
            **kwargs,
        )


class Map3DLayer(pydeck.Layer):
    def __init__(
        self,
        mesh: str = DeckGLMapProps.image,
        property_texture: str = DeckGLMapProps.image,
        color_map_name: str = DeckGLMapProps.colormap,
        name: str = LayerNames.MAP3D,
        bounds: List[float] = DeckGLMapProps.bounds,
        mesh_value_range: List[float] = [0, 1],
        mesh_max_error: int = 5,
        property_value_range: List[float] = [0, 1],
        color_map_range: List[float] = [0, 1],
        contours: List[float] = [0, 100],
        rot_deg: float = 0.0,
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.MAP3D,
            id=uuid if uuid is not None else LayerIds.MAP3D,
            mesh=String(mesh),
            propertyTexture=String(property_texture),
            colorMapName=String(color_map_name),
            name=String(name),
            bounds=bounds,
            meshValueRange=mesh_value_range,
            propertyValueRange=property_value_range,
            colorMapRange=color_map_range,
            meshMaxError=mesh_max_error,
            contours=contours,
            rotDeg=rot_deg,
            **kwargs,
        )


class ColormapLayer(pydeck.Layer):
    def __init__(
        self,
        image: str = DeckGLMapProps.image,
        colormap: str = DeckGLMapProps.colormap,
        name: str = LayerNames.COLORMAP,
        bounds: List[float] = DeckGLMapProps.bounds,
        value_range: List[float] = [0, 1],
        color_map_range: List[float] = [0, 1],
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.COLORMAP,
            id=uuid if uuid is not None else LayerIds.COLORMAP,
            image=String(image),
            colorMapName=String(colormap),
            name=String(name),
            bounds=bounds,
            valueRange=value_range,
            colorMapRange=color_map_range,
            **kwargs,
        )


class WellsLayer(pydeck.Layer):
    def __init__(
        self,
        data: FeatureCollection = None,
        log_data: dict = None,
        log_run: str = None,
        log_name: str = None,
        name: str = LayerNames.WELL,
        selected_well: str = "@@#editedData.selectedWell",
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.WELL,
            id=uuid if uuid is not None else LayerIds.WELL,
            name=String(name),
            data={} if data is None else data,
            logData=log_data,
            logrunName=log_run,
            logName=log_name,
            # selectedWell=String(selected_well),
            **kwargs,
        )


class DrawingLayer(pydeck.Layer):
    def __init__(
        self,
        data: str = "@@#editedData.data",
        selectedFeatureIndexes: str = "@@#editedData.selectedFeatureIndexes",
        mode: Literal[  # Use Enum?
            "view", "modify", "transform", "drawPoint", "drawLineString", "drawPolygon"
        ] = "view",
        uuid: Optional[str] = None,
    ):
        super().__init__(
            type=LayerTypes.DRAWING,
            id=uuid if uuid is not None else LayerIds.DRAWING,
            name=LayerNames.DRAWING,
            data=String(data),
            mode=String(mode),
            selectedFeatureIndexes=String(selectedFeatureIndexes),
        )


class FaultPolygonsLayer(pydeck.Layer):
    def __init__(
        self,
        data: FeatureCollection = None,
        name: str = LayerNames.FAULTPOLYGONS,
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.FAULTPOLYGONS,
            id=uuid if uuid is not None else LayerIds.FAULTPOLYGONS,
            name=String(name),
            data={
                "type": "FeatureCollection",
                "features": [],
            }
            if data is None
            else data,
            **kwargs,
        )


class CustomLayer(pydeck.Layer):
    def __init__(self, type: str, id: str, name: str, **kwargs: Any) -> None:
        super().__init__(type=type, id=String(id), name=String(name), **kwargs)
