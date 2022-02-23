from pathlib import Path
from typing import Callable, List, Tuple, Dict

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings


from .callbacks import plugin_callbacks
from .layout import main_layout
from webviz_subsurface._providers import (
    EnsembleSurfaceProviderFactory,
    WellProviderFactory,
    EnsembleFaultPolygonsProviderFactory,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)
from webviz_subsurface._providers.well_provider.well_server import WellServer
from webviz_subsurface._providers.ensemble_fault_polygons_provider.fault_polygons_server import (
    FaultPolygonsServer,
)


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
        map_surface_names_to_fault_polygons: Dict[str, List[str]] = None,
    ):

        super().__init__()

        surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
        well_provider_factory = WellProviderFactory.instance()
        fault_polygons_provider_factory = (
            EnsembleFaultPolygonsProviderFactory.instance()
        )

        self._ensemble_surface_providers = {
            ens: surface_provider_factory.create_from_ensemble_surface_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens],
                attribute_filter=attributes,
            )
            for ens in ensembles
        }
        self._surface_server = SurfaceServer.instance(app)

        if wellfolder is not None:
            self.well_provider = well_provider_factory.create_from_well_files(
                well_folder=wellfolder, well_suffix=wellsuffix, md_logname=mdlog
            )
            self._well_server = WellServer.instance(app)
            self._well_server.add_provider(self.well_provider)
        else:
            self.well_provider = None
            self._well_server = None

        self._ensemble_fault_polygons_providers = {
            ens: fault_polygons_provider_factory.create_from_ensemble_fault_polygons_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens]
            )
            for ens in ensembles
        }
        self._fault_polygons_server = FaultPolygonsServer.instance(app)
        for fault_polygons_provider in self._ensemble_fault_polygons_providers.values():
            self._fault_polygons_server.add_provider(fault_polygons_provider)

        self.map_surface_names_to_fault_polygons = (
            map_surface_names_to_fault_polygons
            if map_surface_names_to_fault_polygons is not None
            else {}
        )

        self.set_callbacks()

    @property
    def layout(self) -> html.Div:
        reals = []
        for provider in self._ensemble_surface_providers.values():
            reals.extend([x for x in provider.realizations() if x not in reals])
        return main_layout(
            get_uuid=self.uuid,
            well_names=self.well_provider.well_names()
            if self.well_provider is not None
            else [],
            realizations=reals,
        )

    def set_callbacks(self) -> None:

        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self._surface_server,
            well_provider=self.well_provider,
            well_server=self._well_server,
            ensemble_fault_polygons_providers=self._ensemble_fault_polygons_providers,
            fault_polygons_server=self._fault_polygons_server,
            map_surface_names_to_fault_polygons=self.map_surface_names_to_fault_polygons,
        )
