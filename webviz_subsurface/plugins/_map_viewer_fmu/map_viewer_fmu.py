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
    WellProviderFactory,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)
from webviz_subsurface._providers.well_provider.well_server import WellServer
from .routes import deckgl_map_routes  # type: ignore
from .webviz_store import webviz_store_functions


class MapViewerFMU(WebvizPluginABC):
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        attributes: list = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        well_downsample_interval: int = None,
        mdlog: str = None,
        fault_polygon_attribute: str = None,
    ):

        super().__init__()
        # with open("/tmp/drogon_well_picks.json", "r") as f:
        #     self.jsondata = json.load(f)

        # Find surfaces
        provider_factory = EnsembleSurfaceProviderFactory.instance()

        self._ensemble_surface_providers = {
            ens: provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens]
            )
            for ens in ensembles
        }
        self.surface_server = SurfaceServer.instance(app)

        provider_factory = WellProviderFactory.instance()

        self.well_provider = provider_factory.create_from_well_files(
            well_folder=wellfolder, well_suffix=wellsuffix, md_logname=mdlog
        )
        self.well_server = WellServer.instance(app)
        self.well_server.add_provider(self.well_provider)

        # Initialize surface set
        # if attributes is not None:
        #     self._surface_table = self._surface_table[
        #         self._surface_table["attribute"].isin(attributes)
        #     ]
        #     if self._surface_table.empty:
        #         raise ValueError("No surfaces found with the given attributes")

        # Find fault polygons
        # self._fault_polygons_table = scrape_scratch_disk_for_fault_polygons

        self.set_callbacks()

    @property
    def layout(self) -> html.Div:

        return main_layout(
            get_uuid=self.uuid, well_names=self.well_provider.well_names()
        )

    def set_callbacks(self) -> None:

        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self.surface_server,
            well_provider=self.well_provider,
            well_server=self.well_server,
        )
