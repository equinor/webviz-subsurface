from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import pydeck
from geojson.feature import FeatureCollection
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


@dataclass
class Bounds:
    x_min: int = 0
    y_min: int = 0
    x_max: int = 10
    y_max: int = 10


# pylint: disable=too-few-public-methods
class DeckGLMapProps:
    """Default prop settings for DeckGLMap"""

    bounds: List[float] = [0, 0, 10000, 10000]
    value_range: List[float] = [0, 1]
    image: str = "/surface/UNDEF.png"
    color_map_name: str = "Physics"
    edited_data: Dict[str, Any] = {
        "data": {"type": "FeatureCollection", "features": []},
        "selectedWell": "",
        "selectedFeatureIndexes": [],
    }
    resources: Dict[str, Any] = {}


class Hillshading2DLayer(pydeck.Layer):
    def __init__(
        self,
        image: str = DeckGLMapProps.image,
        name: str = LayerNames.HILLSHADING,
        bounds: List[float] = None,
        value_range: List[float] = None,
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.HILLSHADING,
            id=uuid if uuid is not None else LayerIds.HILLSHADING,
            image=String(image),
            name=String(name),
            bounds=bounds if bounds is not None else DeckGLMapProps.bounds,
            valueRange=value_range if value_range is not None else [0, 1],
            **kwargs,
        )


class Map3DLayer(pydeck.Layer):
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        mesh: str = DeckGLMapProps.image,
        property_texture: str = DeckGLMapProps.image,
        color_map_name: str = DeckGLMapProps.color_map_name,
        name: str = LayerNames.MAP3D,
        bounds: List[float] = None,
        mesh_value_range: List[float] = None,
        mesh_max_error: int = 5,
        property_value_range: List[float] = None,
        color_map_range: List[float] = None,
        contours: List[float] = None,
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
            bounds=bounds if bounds is not None else DeckGLMapProps.bounds,
            meshValueRange=mesh_value_range if mesh_value_range is not None else [0, 1],
            propertyValueRange=property_value_range
            if property_value_range is not None
            else [0, 1],
            colorMapRange=color_map_range if color_map_range is not None else [0, 1],
            meshMaxError=mesh_max_error,
            contours=contours if contours is not None else [0, 100],
            rotDeg=rot_deg,
            **kwargs,
        )


class ColormapLayer(pydeck.Layer):
    def __init__(
        self,
        image: str = DeckGLMapProps.image,
        color_map_name: str = DeckGLMapProps.color_map_name,
        name: str = LayerNames.COLORMAP,
        bounds: List[float] = None,
        value_range: List[float] = None,
        color_map_range: List[float] = None,
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.COLORMAP,
            id=uuid if uuid is not None else LayerIds.COLORMAP,
            image=String(image),
            colorMapName=String(color_map_name),
            name=String(name),
            bounds=bounds if bounds is not None else DeckGLMapProps.bounds,
            valueRange=value_range if value_range is not None else [0, 1],
            colorMapRange=color_map_range if color_map_range is not None else [0, 1],
            **kwargs,
        )


class WellsLayer(pydeck.Layer):
    def __init__(
        self,
        data: FeatureCollection = None,
        name: str = LayerNames.WELL,
        uuid: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type="GeoJsonLayer",
            id=uuid if uuid is not None else LayerIds.WELL,
            name=String(name),
            data={"type": "FeatureCollection", "features": []}
            if data is None
            else data,
            get_text="properties.attribute",
            get_text_size=12,
            get_text_anchor=String("start"),
            # logData=log_data,
            # logrunName=log_run,
            # logName=log_name,
            # selectedWell=String(selected_well),
            pointType=String("circle+text"),
            lineWidthMinPixels=2,
            pointRadiusMinPixels=2,
            pickable=True,
            **kwargs,
        )


class DrawingLayer(pydeck.Layer):
    def __init__(
        self,
        mode: Literal[  # Use Enum?
            "view", "modify", "transform", "drawPoint", "drawLineString", "drawPolygon"
        ] = "view",
        uuid: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            type=LayerTypes.DRAWING,
            id=uuid if uuid is not None else LayerIds.DRAWING,
            name=LayerNames.DRAWING,
            mode=String(mode),
            **kwargs,
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
    def __init__(self, layer_type: str, uuid: str, name: str, **kwargs: Any) -> None:
        super().__init__(type=layer_type, id=String(uuid), name=String(name), **kwargs)
