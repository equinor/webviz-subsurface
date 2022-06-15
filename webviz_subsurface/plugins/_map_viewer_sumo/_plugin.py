from dash import Dash
from webviz_config import WebvizPluginABC

from .views._single_map_view import SingleMapView
from ._layout_elements import ElementIds

from .views._single_map_view import SingleMapView

from webviz_subsurface._providers.ensemble_surface_provider import (
    EnsembleProviderDealerSumo,
    EnsembleSurfaceProviderFactory,
)
from webviz_subsurface._providers.ensemble_surface_provider import SurfaceServer

from werkzeug.middleware.proxy_fix import ProxyFix
from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO, WebvizRunMode


class MapViewerSumo(WebvizPluginABC):
    """Surface visualizer for FMU ensembles using SUMO."""

    # pylint: disable=too-many-arguments
    def __init__(self, app: Dash, field_name: str):
        super().__init__(stretch=True)

        self._use_oauth2 = (
            True if WEBVIZ_INSTANCE_INFO.run_mode == WebvizRunMode.PORTABLE else False
        )

        app.server.wsgi_app = ProxyFix(app.server.wsgi_app, x_proto=1, x_host=1)

        # For now, just touch the factory to initialize it here
        EnsembleSurfaceProviderFactory.instance()

        provider_dealer = EnsembleProviderDealerSumo(use_session_token=self._use_oauth2)
        surface_server = SurfaceServer.instance(app)

        self.add_store(
            ElementIds.STORES.CASE_ITER_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            ElementIds.STORES.SURFACE_ADDRESS_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        self.add_view(
            SingleMapView(
                provider_dealer=provider_dealer,
                field_name=field_name,
                surface_server=surface_server,
            ),
            ElementIds.SINGLEMAPVIEW.ID,
        )

    @property
    def oauth2(self):
        return self._use_oauth2
