import copy
import re
import json
from typing import List, Dict
import jsonpatch, jsonpointer
from dash import no_update


class DeckGLMapController:
    COLORMAP_ID = "colormap-layer"
    HILLSHADING_ID = "hillshading-layer"
    PIE_ID = "pie-layer"
    WELLS_ID = "wells-layer"
    DRAWING_ID = "drawing-layer"

    def __init__(self, current_spec=None, current_resources=None, client_patch=None):
        self._spec = current_spec if current_spec else {}
        self._client_patch = self._normalize_patch(client_patch) if client_patch else []
        if self._client_patch:

            jsonpatch.apply_patch(self._spec, self._client_patch, in_place=True)
        self._prev_spec = copy.deepcopy(current_spec) if current_spec else {}
        self._resources = current_resources if current_resources is not None else {}
        self._prev_resources = copy.deepcopy(current_resources)

    def _layer_idx_from_id(self, layer_id):
        """Retrieves the layer index in the specification from a given layer id.
        Raises a value error if the layer is not found."""
        for layer_idx, layer in enumerate(self._prev_spec.get("layers", [])):
            if layer["id"] == layer_id:
                return layer_idx
        raise ValueError(f"Layer with id {layer_id} not found in specification.")

    def _normalize_patch(self, in_patch, inplace=False):
        """Converts all layer ids to layer indices in a given patch.
        The patch path looks something like this: `/layers/[layer-id]/property`,
        where `[layer-id]` is the id of an object in the `layers` array.
        This function will replace all object ids with their indices in the array,
        resulting in a path that would look like this: `/layers/2/property`,
        which is a valid json pointer that can be used by json patch."""

        def replace_path_id(matched):
            parent = matched.group(1)
            obj_id = matched.group(2)
            parent_array = jsonpointer.resolve_pointer(self._spec, parent)
            matched_id = -1
            for (i, elem) in enumerate(parent_array):
                if elem["id"] == obj_id:
                    matched_id = i
                    break
            if matched_id < 0:
                raise f"Id {obj_id} not found"
            return f"{parent}/{matched_id}"

        out_patch = in_patch if inplace else copy.deepcopy(in_patch)
        for patch in out_patch:
            patch["path"] = re.sub(
                r"([\w\/-]*)\/\[([\w-]+)\]", replace_path_id, patch["path"]
            )

        return out_patch

    def set_surface_data(
        self,
        image: str,
        range: List[float],
        bounds: List[List[float]],
        target: List[float],
    ):
        """Updates the resources with map data."""
        patch_resources = {
            "mapImage": image,
            "mapRange": range,
            "mapBounds": bounds,
            "mapTarget": target,
        }
        self._resources.update(patch_resources)

    def set_well_data(self, data: Dict):
        """Updates the resources with well data"""
        patch_resources = {"wellData": data}
        self._resources.update(patch_resources)

    def update_colormap(self, colormap="viridis_r"):
        layer_idx = self._layer_idx_from_id(self.COLORMAP_ID)
        self._spec["layers"][layer_idx]["colormap"] = f"/colormaps/{colormap}.png"

    def update_colormap_range(self, value_range):
        layer_idx = self._layer_idx_from_id(self.COLORMAP_ID)
        self._spec["layers"][layer_idx]["colorMapRange"] = value_range

    def update_pie_data(self, pie_data: Dict[str, List[Dict]]):
        layer_idx = self._layer_idx_from_id(self.PIE_ID)
        self._spec["layers"][layer_idx]["data"] = pie_data

    @property
    def _drawing_layer_selected_feature(self):
        layer_idx = self._layer_idx_from_id(self.DRAWING_ID)

        drawing_layer = self._spec["layers"][layer_idx]
        selected_feature_idx = drawing_layer.get("selectedFeatureIndexes")
        for idx, feature in enumerate(drawing_layer["data"]["features"]):
            if idx == selected_feature_idx[0]:
                return feature

    def get_polylines(self):
        """Returns coordinates of any drawn polylines"""
        if not self._drawing_layer_selected_feature:
            return None
        if (
            self._drawing_layer_selected_feature.get("geometry", {}).get("type")
            == "LineString"
        ):
            return self._drawing_layer_selected_feature["geometry"].get(
                "coordinates", []
            )
        return None

    def clear_drawing_layer(self):
        layer_idx = self._layer_idx_from_id(self.DRAWING_ID)
        self._spec["layers"][layer_idx]["data"] = {
            "type": "FeatureCollection",
            "features": [],
        }

    @classmethod
    def selected_wells_from_patch(cls, patch_list):
        """Checks patches for `selectedFeature` on the well layer.
        A list of matched well names is returned."""
        path = f"/layers/[{cls.WELLS_ID}]/selectedFeature"
        return (
            []
            if not patch_list
            else [
                patch["value"]["properties"]["name"]
                for patch in patch_list
                if (patch["op"] == "add" and path in patch["path"])
            ]
        )

    def get_selected_well(self):
        """Get selected well from spec"""
        layer_idx = self._layer_idx_from_id(self.WELLS_ID)
        feature = self._spec["layers"][layer_idx].get("selectedFeature")
        if feature is None:
            return None
        return feature.get("properties", {}).get("name", None)

    @property
    def spec_patch(self):
        return jsonpatch.make_patch(self._prev_spec, self._spec).patch

    @property
    def resources(self):
        return no_update if self._resources == self._prev_resources else self._resources
