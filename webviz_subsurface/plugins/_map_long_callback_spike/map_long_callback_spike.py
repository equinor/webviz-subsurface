import json
from pathlib import Path
from typing import Callable, List, Tuple

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings


from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files, get_path

from .callbacks import plugin_callbacks
from .layout import main_layout
from webviz_subsurface._providers import (
    EnsembleSurfaceProviderFactory,
    EnsembleSurfaceProvider,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)


class MapLongCallbackSpike(WebvizPluginABC):
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
    ):

        super().__init__()

        # Find surfaces
        provider_factory = EnsembleSurfaceProviderFactory.instance()
        self.provider: EnsembleSurfaceProvider = ()
        self._ensemble_surface_providers = {
            ens: provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens]
            )
            for ens in ensembles
        }
        self.surface_server = SurfaceServer.instance(app)

        self.set_callbacks()

    @property
    def layout(self) -> html.Div:

        return main_layout(get_uuid=self.uuid)

    def set_callbacks(self) -> None:

        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self.surface_server,
        )
