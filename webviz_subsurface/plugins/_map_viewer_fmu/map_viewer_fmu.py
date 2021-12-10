import json
from pathlib import Path
from typing import Callable, List, Tuple

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings


from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files, get_path

from .callbacks import plugin_callbacks
from .layout import main_layout
from .providers.ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    scrape_scratch_disk_for_surfaces,
)
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
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        # Find surfaces
        self._surface_table = scrape_scratch_disk_for_surfaces(self.ens_paths)

        # Initialize surface set
        if attributes is not None:
            self._surface_table = self._surface_table[
                self._surface_table["attribute"].isin(attributes)
            ]
            if self._surface_table.empty:
                raise ValueError("No surfaces found with the given attributes")
        self._ensemble_surface_providers = {
            ens: EnsembleSurfaceProvider(surf_ens_df)
            for ens, surf_ens_df in self._surface_table.groupby("ENSEMBLE")
        }

        # Find fault polygons
        # self._fault_polygons_table = scrape_scratch_disk_for_fault_polygons

        # Find wells
        self._wellfolder = wellfolder
        self._wellsuffix = wellsuffix
        self._wellfiles: List = (
            json.load(find_files(folder=self._wellfolder, suffix=self._wellsuffix))
            if self._wellfolder is not None
            else None
        )

        # Initialize well set
        self._well_set_model = (
            WellSetModel(
                self._wellfiles,
                mdlog=mdlog,
                downsample_interval=well_downsample_interval,
            )
            if self._wellfiles
            else None
        )

        self.set_callbacks()
        self.set_routes(app)

    @property
    def layout(self) -> html.Div:

        return main_layout(get_uuid=self.uuid, well_set_model=self._well_set_model)

    def set_callbacks(self) -> None:

        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            well_set_model=self._well_set_model,
        )

    def set_routes(self, app: Dash) -> None:
        deckgl_map_routes(
            app=app,
            ensemble_surface_providers=self._ensemble_surface_providers,
            well_set_model=self._well_set_model,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:

        store_functions = webviz_store_functions(
            ensemble_surface_providers=self._ensemble_surface_providers,
            ensemble_paths=self.ens_paths,
        )
        if self._wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self._wellfolder, "suffix": self._wellsuffix}])
            )
            store_functions.extend(
                [(get_path, [{"path": fn}]) for fn in self._wellfiles]
            )
        return store_functions
