from typing import List
from enum import Enum

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
    DeckGLMapDefaultProps,
)


class DeckGLMapAIOIds(str, Enum):
    """An enum for the internal ids used in the DeckGLMapAIO component"""

    MAP = "map"
    PROPERTYMAP_IMAGE = "propertymap_image"
    PROPERTYMAP_RANGE = "propertymap_range"
    PROPERTYMAP_BOUNDS = "propertymap_bounds"
    COLORMAP_IMAGE = "colormap_image"
    COLORMAP_RANGE = "colormap_range"
    WELL_DATA = "well_data"
    SELECTED_WELL = "selected_well"
    EDITED_FEATURES = "edited_features"
    SELECTED_FEATURES = "selected_features"


class DeckGLMapAIO(html.Div):
    """A Dash 'All-in-one component' that can be used for the wsc.DeckGLMap component. The main difference from using the
    wsc.DeckGLMap component directly is that this AIO exposes more props so that different updates to the layer specification,
    and reacting to selected data can be done in different callbacks in a webviz plugin.

    The AIO component might have limitations for some use cases, if so use the wsc.DeckGLMap component directly.

    To handle layer updates a separate class is used. This class - DeckGLMapLayersModel can also be used directly with the wsc.DeckGLMap.

    As usage and functionality of DeckGLMap matures this component might be integrated in the React component directly.

    To use this AIO component, initialize it in the layout of a webviz plugin.
    """

    class ids:
        """Namespace holding internal ids of the component. Each id is a lambda function set in the loop below."""

        pass

    for id_name in DeckGLMapAIOIds:
        setattr(
            ids,
            id_name,
            lambda aio_id, id_name=id_name: {
                "component": "DeckGLMapAIO",
                "subcomponent": id_name,
                "aio_id": aio_id,
            },
        )

    def __init__(self, aio_id, layers: List[pdk.Layer]):
        """
        The DeckGLMapAIO component should be initialized in the layout of a webviz plugin.
        Args:
            aio_id: unique id
            layers: list of pydeck Layers
        """
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
                dcc.Store(data=[], id=self.ids.selected_well(aio_id)),
                dcc.Store(data={}, id=self.ids.well_data(aio_id)),
                dcc.Store(data={}, id=self.ids.edited_features(aio_id)),
                dcc.Store(data={}, id=self.ids.selected_features(aio_id)),
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
        """Callback handling all updates to the layers prop of the Map component"""

        layer_model = DeckGLMapLayersModel(current_layers)
        layer_model.set_propertymap(
            image_url=propertymap_image,
            bounds=propertymap_bounds,
            value_range=propertymap_range,
        )
        layer_model.set_colormap_image(colormap_image)
        layer_model.set_colormap_range(colormap_range)
        if well_data is not None:
            layer_model.set_well_data(well_data)

        return layer_model.layers, propertymap_bounds

    @callback(
        Output(ids.edited_features(MATCH), "data"),
        Output(ids.selected_features(MATCH), "data"),
        Input(ids.map(MATCH), "editedData"),
    )
    def _get_edited_features(
        edited_data,
    ):
        """Callback that stores any selected data in internal dcc.store components"""
        if edited_data is not None:
            from dash import no_update

        return no_update