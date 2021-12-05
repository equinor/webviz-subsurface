from enum import Enum
from typing import Any, Dict, List
from geojson.feature import FeatureCollection

import pydeck
from pydeck.types import String
from typing_extensions import Literal


class LayerTypes(str, Enum):
    HILLSHADING = "Hillshading2DLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"
    DRAWING = "DrawingLayer"


class LayerIds(str, Enum):
    HILLSHADING = "hillshading-layer"
    COLORMAP = "colormap-layer"
    WELL = "wells-layer"
    DRAWING = "drawing-layer"


class LayerNames(str, Enum):
    HILLSHADING = "Hillshading"
    COLORMAP = "Colormap"
    WELL = "Wells"
    DRAWING = "Drawings"


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
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.HILLSHADING,
            id=LayerIds.HILLSHADING,
            image=String(image),
            name=String(name),
            bounds=bounds,
            valueRange=value_range,
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
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.COLORMAP,
            id=LayerIds.COLORMAP,
            image=String(image),
            colormap=String(colormap),
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
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.WELL,
            id=LayerIds.WELL,
            name=String(name),
            data={} if data is None else data,
            logData=log_data,
            logrunName=log_run,
            logName=log_name,
            selectedWell=String(selected_well),
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
    ):
        super().__init__(
            type=LayerTypes.DRAWING,
            id=LayerIds.DRAWING,
            name=LayerNames.DRAWING,
            data=String(data),
            mode=String(mode),
            selectedFeatureIndexes=String(selectedFeatureIndexes),
        )


class CustomLayer(pydeck.Layer):
    def __init__(self, type: str, id: str, name: str, **kwargs: Any) -> None:
        super().__init__(type=type, id=String(id), name=String(name), **kwargs)
