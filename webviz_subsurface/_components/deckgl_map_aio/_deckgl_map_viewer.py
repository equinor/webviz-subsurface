from typing import Dict
from functools import wraps

from webviz_subsurface_components import DeckGLMap


class DeckGLMapViewer(DeckGLMap):
    """A wrapper for `DeckGLMap` with default props set.
    This class is used in conjunction with the `DeckGLMapController,
    to simplify some of the logic necessary to initialize and update
    the `DeckGLMap` component.

    * surface: bool, Adds a colormap and hillshading layer
    * wells: bool, Adds a well layer
    * fault_polygons: bool, Adds fault polygon layer
    * pie_charts: bool, Adds pie chart layer
    * drawing: bool, Adds a drawing layer
    """

    @wraps(DeckGLMap)
    def __init__(
        self,
        surface: bool = True,
        wells: bool = False,
        fault_polygons: bool = False,
        pie_charts: bool = False,
        drawing: bool = False,
        **kwargs,
    ) -> None:
        self._layers = self._set_layers(
            surface=surface,
            wells=wells,
            fault_polygons=fault_polygons,
            pie_charts=pie_charts,
            drawing=drawing,
        )
        props = self._default_props
        if "deckglSpecBase" in kwargs:
            kwargs = kwargs.pop("deckglSpecBase")
        props.update(kwargs)
        super(DeckGLMapViewer, self).__init__(**props)

    @property
    def _default_props(self):
        return {
            # "coords": {"visible": True, "multiPicking": True, "pickDepth": 10},
            # "scale": {
            #     "visible": True,
            #     "incrementValue": 100,
            #     "widthPerUnit": 100,
            #     "position": [10, 10],
            # },
            "resources": self._resources_spec,
            "coordinateUnit": "m",
            "deckglSpecBase": {
                "initialViewState": {
                    "target": "@@#resources.mapTarget",
                    "zoom": -4,
                },
                "layers": self._layers,
            },
        }

    @property
    def layers(self):
        return self._layers

    @property
    def _resources_spec(self):
        return {
            "mapImage": "/image/dummy.png",
            "mapBounds": [0, 1, 0, 1],
            "mapRange": [0, 1],
            "mapTarget": [0.5, 0.5, 0],
            "wellData": {"type": "FeatureCollection", "features": []},
            "logData": [],
        }

    @property
    def _colormap_spec(self) -> Dict:
        return {
            "@@type": "ColormapLayer",
            # pylint: disable=line-too-long
            "colormap": "/colormaps/viridis_r.png",
            "id": "colormap-layer",
            "pickable": True,
            "image": "@@#resources.mapImage",
            "valueRange": "@@#resources.mapRange",
            "bounds": "@@#resources.mapBounds",
        }

    @property
    def _hillshading_spec(self) -> Dict:
        return {
            "@@type": "Hillshading2DLayer",
            "id": "hillshading-layer",
            "pickable": True,
            "image": "@@#resources.mapImage",
            "valueRange": "@@#resources.mapRange",
            "bounds": "@@#resources.mapBounds",
        }

    @property
    def _wells_spec(self) -> Dict:
        return {
            "@@type": "WellsLayer",
            "id": "wells-layer",
            "description": "wells",
            "data": "@@#resources.wellData",
            "logData": "@@#resources.logData",
            "opacity": 1.0,
            "lineWidthScale": 5,
            "pointRadiusScale": 8,
            "outline": True,
            "logCurves": True,
            "refine": True,
            "pickable": True,
        }

    @property
    def _pies_spec(self) -> Dict:
        return {
            "@@type": "PieChartLayer",
            "id": "pie-layer",
        }

    @property
    def _drawing_spec(self) -> Dict:
        return {
            "@@type": "DrawingLayer",
            "id": "drawing-layer",
            "mode": "view",
            "data": {"type": "FeatureCollection", "features": []},
        }

    def _set_layers(
        self,
        surface: bool = True,
        fault_polygons: bool = False,
        wells: bool = False,
        pie_charts: bool = False,
        drawing: bool = False,
    ):
        layers = []
        if surface:
            layers.append(self._colormap_spec)
            layers.append(self._hillshading_spec)
        if wells:
            layers.append(self._wells_spec)
        if pie_charts:
            layers.append(self._pies_spec)
        if fault_polygons:
            pass
        if drawing:
            layers.append(self._drawing_spec)
        return layers
