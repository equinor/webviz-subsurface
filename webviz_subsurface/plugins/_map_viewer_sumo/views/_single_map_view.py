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

from webviz_subsurface._providers.ensemble_surface_provider import (
    EnsembleProviderDealer,
    SimulatedSurfaceAddress,
    StatisticalSurfaceAddress,
    SurfaceServer,
    QualifiedSurfaceAddress,
)

from .settings._surface_selectors import AGGREGATIONS


class SingleMapView(ViewABC):
    def __init__(
        self,
        provider_dealer: EnsembleProviderDealer,
        field_name: str,
        surface_server: SurfaceServer,
    ) -> None:
        super().__init__("Single Surface View")
        self._provider_dealer = provider_dealer
        self._field_name = field_name
        self._surface_server = surface_server
        self.add_view_element(DeckGLView(), ElementIds.DECKGLVIEW.ID),
        self.add_settings_group(
            CaseSelector(provider_dealer=provider_dealer, field_name=field_name),
            ElementIds.CASE_SELECTOR.ID,
        )
        self.add_settings_group(
            SurfaceSelector(provider_dealer=provider_dealer, field_name=field_name),
            ElementIds.SURFACE_SELECTOR.ID,
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ElementIds.DECKGLVIEW.ID)
                .component_unique_id(ElementIds.DECKGLVIEW.VIEW)
                .to_string(),
                "bounds",
            ),
            Output(
                self.view_element(ElementIds.DECKGLVIEW.ID)
                .component_unique_id(ElementIds.DECKGLVIEW.VIEW)
                .to_string(),
                "layers",
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
            # print(f"callback _update_map_component() {surface_address=}")

            if not surface_address:
                return no_update

            undecided_address: SurfaceAddress = SurfaceAddress(**surface_address)
            case = undecided_address.case_name
            iteration = undecided_address.iteration_name
            if undecided_address.aggregation == AGGREGATIONS.SINGLE_REAL:
                surface_address = SimulatedSurfaceAddress(
                    attribute=undecided_address.surface_attribute,
                    name=undecided_address.surface_name,
                    datestr=undecided_address.surface_date,
                    realization=int(undecided_address.realizations[0]),
                )
            else:
                surface_address = StatisticalSurfaceAddress(
                    attribute=undecided_address.surface_attribute,
                    name=undecided_address.surface_name,
                    datestr=undecided_address.surface_date,
                    realizations=[int(real) for real in undecided_address.realizations],
                    statistic=undecided_address.aggregation,
                )
            provider = self._provider_dealer.get_surface_provider(
                field_name=self._field_name,
                case_name=case,
                iteration_id=iteration,
            )
            # surface = provider.get_surface(surface_address)
            provider_id = provider.provider_id()
            qualified_address = QualifiedSurfaceAddress(provider_id, surface_address)
            surf_meta = self._surface_server.get_surface_metadata(qualified_address)
            if not surf_meta:
                # This means we need to compute the surface
                surface = provider.get_surface(address=surface_address)
                if not surface:
                    raise ValueError(
                        f"Could not get surface for address: {surface_address}"
                    )
                self._surface_server.publish_surface(qualified_address, surface)
                surf_meta = self._surface_server.get_surface_metadata(qualified_address)
            viewport_bounds = [
                surf_meta.x_min,
                surf_meta.y_min,
                surf_meta.x_max,
                surf_meta.y_max,
            ]
            layer_data = {
                "image": self._surface_server.encode_partial_url(qualified_address),
                "bounds": surf_meta.deckgl_bounds,
                "rotDeg": surf_meta.deckgl_rot_deg,
                "valueRange": [surf_meta.val_min, surf_meta.val_max],
                "@@type": "ColormapLayer",
            }
            return viewport_bounds, [layer_data]
