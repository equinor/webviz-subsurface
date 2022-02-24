import warnings
from enum import Enum
from typing import Dict, List

from .types.deckgl_props import LayerTypes


class DeckGLMapLayersModel:
    """Handles updates to the DeckGLMap layers prop"""

    def __init__(self, layers: List[Dict]) -> None:
        self._layers = layers

    def _update_layer_by_type(self, layer_type: Enum, layer_data: Dict) -> None:
        """Update a layer specification by the layer type. If multiple layers are found,
        no update is performed."""
        layers = list(filter(lambda x: x["@@type"] == layer_type, self._layers))
        if not layers:
            warnings.warn(f"No {layer_type} found in layer specification!")
        if len(layers) > 1:
            warnings.warn(
                f"Multiple layers of type {layer_type} found in layer specification!"
            )
        if len(layers) == 1:
            layer_idx = self._layers.index(layers[0])
            self._layers[layer_idx].update(layer_data)

    def update_layer_by_id(self, layer_id: str, layer_data: Dict) -> None:
        """Update a layer specification by the layer id."""
        layers = list(filter(lambda x: x["id"] == layer_id, self._layers))
        if not layers:
            warnings.warn(f"No layer with id {layer_id} found in layer specification!")
        if len(layers) > 1:
            warnings.warn(
                f"Multiple layers with id {layer_id} found in layer specification!"
            )
        if len(layers) == 1:
            layer_idx = self._layers.index(layers[0])
            self._layers[layer_idx].update(layer_data)

    def set_propertymap(
        self,
        image_url: str,
        bounds: List[float],
        value_range: List[float],
    ) -> None:
        """Set the property map image url, bounds and value range in the
        Colormap and Hillshading layer"""
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

    def set_colormap_image(self, colormap: str) -> None:
        """Set the colormap image url in the ColormapLayer"""
        self._update_layer_by_type(
            layer_type=LayerTypes.COLORMAP,
            layer_data={
                "colormap": colormap,
            },
        )

    def set_colormap_range(self, colormap_range: List[float]) -> None:
        """Set the colormap range in the ColormapLayer"""
        self._update_layer_by_type(
            layer_type=LayerTypes.COLORMAP,
            layer_data={
                "colorMapRange": colormap_range,
            },
        )

    def set_well_data(self, well_data: List[Dict]) -> None:
        """Set the well data json url in the WellsLayer"""
        self._update_layer_by_type(
            layer_type=LayerTypes.WELL,
            layer_data={
                "data": well_data,
            },
        )

    @property
    def layers(self) -> List[Dict]:
        """Returns the full layers specification"""
        return self._layers
