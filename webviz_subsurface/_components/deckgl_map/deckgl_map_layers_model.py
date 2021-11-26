from typing import Dict, List
from enum import Enum

from .deckgl_map import LayerTypes


class DeckGLMapLayersModel:
    """Handles updates to the DeckGLMap layers prop"""

    def __init__(self, layers: List[Dict]) -> None:
        self._layers = layers

    def _update_layer_by_type(self, layer_type: Enum, layer_data: Dict):
        layers = list(filter(lambda x: x["@@type"] == layer_type, self._layers))
        # if not layers:
        #     raise KeyError(f"No {layer_type} found in layer specification!")
        # if len(layers) > 1:
        #     raise KeyError(
        #         f"Multiple layers of type {layer_type} found in layer specification!"
        #     )
        if len(layers) == 1:
            layer_idx = self._layers.index(layers[0])
            self._layers[layer_idx].update(layer_data)

    def set_propertymap(
        self,
        image_url: str,
        bounds: List[float],
        value_range: List[float],
    ):
        self._update_layer_by_type(
            layer_type=LayerTypes.HILLSHADING,
            layer_data={
                "image": image_url,
                "bounds": bounds,
                "valueRange": value_range,
            },
        )
        self._update_layer_by_type(
            layer_type=LayerTypes.COLORMAP,
            layer_data={
                "image": image_url,
                "bounds": bounds,
                "valueRange": value_range,
            },
        )

    def set_colormap_image(self, colormap: str):
        self._update_layer_by_type(
            layer_type=LayerTypes.COLORMAP,
            layer_data={
                "colormap": colormap,
            },
        )

    def set_colormap_range(self, colormap_range: List[float]):
        self._update_layer_by_type(
            layer_type=LayerTypes.COLORMAP,
            layer_data={
                "colorMapRange": colormap_range,
            },
        )

    def set_well_data(self, well_data: List[Dict]):
        self._update_layer_by_type(
            layer_type=LayerTypes.WELL,
            layer_data={
                "data": well_data,
            },
        )

    @property
    def layers(self) -> Dict:
        return self._layers
