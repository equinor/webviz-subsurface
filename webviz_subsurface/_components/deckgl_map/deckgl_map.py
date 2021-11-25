from typing import List, Dict, Union, Any
from enum import Enum
import json

import pydeck
from pydeck.types import String
from webviz_subsurface_components import DeckGLMap as DeckGLMapBase


class LayerTypes(str, Enum):
    HILLSHADING = "Hillshading2DLayer"
    COLORMAP = "ColormapLayer"
    WELL = "WellsLayer"


class LayerIds(str, Enum):
    HILLSHADING = "hillshading-layer"
    COLORMAP = "colormap-layer"
    WELL = "wells-layer"


class DeckGLMapDefaultProps:
    bounds: List[float] = [0, 0, 10000, 10000]
    value_range: List[float] = [0, 1]
    image: str = "/surface/UNDEF.png"
    colormap: str = "/colormaps/viridis_r.png"
    edited_data: Dict[str, Any] = {
        "selectedDrawingFeature": [],
        "data": {"type": "FeatureCollection", "features": []},
        "selectedWell": "",
        "selectedFeatureIndexes": [],
    }


class DeckGLMap(DeckGLMapBase):
    def __init__(
        self,
        id: Union[str, Dict[str, str]],
        layers: List[pydeck.Layer],
        bounds: List[float] = DeckGLMapDefaultProps.bounds,
        edited_data: Dict[str, Any] = DeckGLMapDefaultProps.edited_data,
        **kwargs,
    ) -> None:
        super().__init__(
            id=id,
            layers=[json.loads(layer.to_json()) for layer in layers],
            bounds=bounds,
            editedData=edited_data,
            **kwargs,
        )


class Hillshading2DLayer(pydeck.Layer):
    def __init__(
        self,
        image: str = DeckGLMapDefaultProps.image,
        name: str = "Hillshading",
        bounds: List[float] = DeckGLMapDefaultProps.bounds,
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
        image: str = DeckGLMapDefaultProps.image,
        colormap: str = DeckGLMapDefaultProps.colormap,
        name: str = "Color map",
        bounds: List[float] = DeckGLMapDefaultProps.bounds,
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
        data,
        log_data=None,
        log_run=None,
        log_name=None,
        name: str = "Wells",
        selected_well: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            type=LayerTypes.WELL,
            id=LayerIds.WELL,
            data=data,
            logData=log_data,
            logrunName=log_run,
            logName=log_name,
            name=String(name),
            selectedWell=String(selected_well),
            **kwargs,
        )
