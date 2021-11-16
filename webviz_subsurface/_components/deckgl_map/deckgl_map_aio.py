from typing import Dict
from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    MATCH,
)

import pydeck as pdk
from .deckgl_map_layers_model import (
    DeckGLMapLayersModel,
)
from .deckgl_map import (
    DeckGLMap,
    Hillshading2DLayer,
    ColormapLayer,
    DeckGLMapDefaultProps,
)


class DeckGLMapAIO(html.Div):
    class ids:
        map = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "map",
            "aio_id": aio_id,
        }
        propertymap_image = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "propertymap_image",
            "aio_id": aio_id,
        }
        propertymap_range = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "propertymap_range",
            "aio_id": aio_id,
        }
        propertymap_bounds = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "propertymap_bounds",
            "aio_id": aio_id,
        }

        colormap_image = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "colormap_image",
            "aio_id": aio_id,
        }
        colormap_range = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "colormap_range",
            "aio_id": aio_id,
        }
        well_data = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "well_data",
            "aio_id": aio_id,
        }

        polylines = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "polylines",
            "aio_id": aio_id,
        }
        selected_well = lambda aio_id: {
            "component": "DeckGLMapAIO",
            "subcomponent": "selected_well",
            "aio_id": aio_id,
        }

    ids = ids

    def __init__(self, aio_id, show_wells: bool = False, well_layer: pdk.Layer = None):
        """"""
        layers = [ColormapLayer(), Hillshading2DLayer()]
        if show_wells and well_layer:
            layers.append(well_layer)
        super().__init__(
            [
                dcc.Store(data=[], id=self.ids.colormap_image(aio_id)),
                dcc.Store(data=[], id=self.ids.colormap_range(aio_id)),
                dcc.Store(
                    data=DeckGLMapDefaultProps.image,
                    id=self.ids.propertymap_image(aio_id),
                ),
                dcc.Store(
                    data=DeckGLMapDefaultProps.value_range,
                    id=self.ids.propertymap_range(aio_id),
                ),
                dcc.Store(
                    data=DeckGLMapDefaultProps.bounds,
                    id=self.ids.propertymap_bounds(aio_id),
                ),
                dcc.Store(data=[], id=self.ids.polylines(aio_id)),
                dcc.Store(data=[], id=self.ids.selected_well(aio_id)),
                dcc.Store(data={}, id=self.ids.well_data(aio_id)),
                DeckGLMap(
                    id=self.ids.map(aio_id),
                    layers=layers,
                ),
            ]
        )

    @callback(
        Output(ids.map(MATCH), "layers"),
        Output(ids.map(MATCH), "bounds"),
        Input(ids.colormap_image(MATCH), "data"),
        Input(ids.colormap_range(MATCH), "data"),
        Input(ids.propertymap_image(MATCH), "data"),
        Input(ids.propertymap_range(MATCH), "data"),
        Input(ids.propertymap_bounds(MATCH), "data"),
        Input(ids.well_data(MATCH), "data"),
        State(ids.map(MATCH), "layers"),
    )
    def _update_deckgl_layers(
        colormap_image,
        colormap_range,
        propertymap_image,
        propertymap_range,
        propertymap_bounds,
        well_data,
        current_layers,
    ):

        layer_model = DeckGLMapLayersModel(current_layers)
        layer_model.set_propertymap(
            image_url=propertymap_image,
            bounds=propertymap_bounds,
            value_range=propertymap_range,
        )
        layer_model.set_colormap_image(colormap_image)
        layer_model.set_colormap_range(colormap_range)
        # if well_data is not None:
        #     layer_model.set_well_data(well_data)

        return layer_model.layers, propertymap_bounds