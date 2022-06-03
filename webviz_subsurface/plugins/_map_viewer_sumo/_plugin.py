from dash import Dash
from webviz_config import WebvizPluginABC

from .views._single_map_view import SingleMapView
from ._layout_elements import ElementIds

from .views._single_map_view import SingleMapView

from webviz_subsurface._providers.ensemble_surface_provider import (
    EnsembleProviderDealer_sumo,
)


class MapViewerSumo(WebvizPluginABC):
    """Surface visualizer for FMU ensembles using SUMO."""

    # pylint: disable=too-many-arguments
    def __init__(self, app: Dash, field_name: str):
        super().__init__(stretch=True)

        provider_dealer = EnsembleProviderDealer_sumo(False)

        self.add_store(
            ElementIds.STORES.CASE_ITER_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            ElementIds.STORES.SURFACE_ADDRESS_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_view(
            SingleMapView(provider_dealer=provider_dealer, field_name=field_name),
            ElementIds.SINGLEMAPVIEW.ID,
        )
