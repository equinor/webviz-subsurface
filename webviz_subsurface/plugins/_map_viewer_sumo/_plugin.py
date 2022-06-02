from dash import Dash
from webviz_config import WebvizPluginABC

from .views._single_map_view import SingleMapView
from ._layout_elements import ElementIds


class MapViewerSumo(WebvizPluginABC):
    """Surface visualizer for FMU ensembles using SUMO."""

    # pylint: disable=too-many-arguments
    def __init__(self, app: Dash, field_name: str = "Drogon"):
        super().__init__(stretch=True)
        self.add_store(
            ElementIds.STORES.CASE_ITER_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            ElementIds.STORES.SURFACE_ADDRESS_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_view(
            SingleMapView(field_name=field_name),
            ElementIds.SINGLEMAPVIEW.ID,
        )
