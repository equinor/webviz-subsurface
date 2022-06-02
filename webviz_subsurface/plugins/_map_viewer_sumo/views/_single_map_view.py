from typing import List, Tuple, Dict, Optional

from dash import Input, Output, State, callback, no_update
from webviz_config.webviz_plugin_subclasses import (
    ViewABC,
)

from .settings._case_selector import CaseSelector
from .settings._surface_selectors import SurfaceSelector
from .view_elements._deckgl_view import DeckGLView

from .._layout_elements import ElementIds
from .settings._surface_selectors import SurfaceAddress


class SingleMapView(ViewABC):
    def __init__(self, field_name: str) -> None:
        super().__init__("Single Surface View")
        self.add_view_element(DeckGLView(), ElementIds.DECKGLVIEW.ID),
        self.add_settings_group(
            CaseSelector(field_name=field_name), ElementIds.CASE_SELECTOR.ID
        )
        self.add_settings_group(
            SurfaceSelector(field_name=field_name), ElementIds.SURFACE_SELECTOR.ID
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ElementIds.DECKGLVIEW.ID)
                .component_unique_id(ElementIds.DECKGLVIEW.VIEW)
                .to_string(),
                "views",
            ),
            Input(
                self.get_store_unique_id(ElementIds.STORES.SURFACE_ADDRESS_STORE),
                "data",
            ),
            State(
                self.view_element(ElementIds.DECKGLVIEW.ID)
                .component_unique_id(ElementIds.DECKGLVIEW.VIEW)
                .to_string(),
                "views",
            ),
        )
        def _update_map_component(surface_address: Dict, views: Dict) -> Dict:
            if not surface_address:
                return no_update, no_update

            # surface_address = SurfaceAddress(**surface_address)

            # Do DeckGL stuff here
            import json

            views["viewports"][0]["name"] = str(json.dumps(surface_address))
            return views
