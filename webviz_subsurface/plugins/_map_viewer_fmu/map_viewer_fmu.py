from pathlib import Path
from typing import Callable, List, Tuple, Dict

import pandas as pd
from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings


from .callbacks import plugin_callbacks
from .layout import main_layout
from ._tmp_well_pick_provider import WellPickProvider

from webviz_subsurface._providers import (
    EnsembleSurfaceProviderFactory,
    EnsembleFaultPolygonsProviderFactory,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)
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
        well_pick_file: Path = None,
        fault_polygon_attribute: str = None,
        map_surface_names_to_fault_polygons: Dict[str, str] = None,
        map_surface_names_to_well_pick_names: Dict[str, str] = None,
    ):

        super().__init__()

        surface_provider_factory = EnsembleSurfaceProviderFactory.instance()
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

        self.well_pick_provider = None
        if well_pick_file is not None:
            well_pick_table = pd.read_csv(well_pick_file)
            self.well_pick_provider = WellPickProvider(
                dframe=well_pick_table,
                map_surface_names_to_well_pick_names=map_surface_names_to_well_pick_names,
            )
            self.well_pick_provider.get_geojson(
                self.well_pick_provider.well_names(), "TopVolantis"
            )

        self._ensemble_fault_polygons_providers = {
            ens: fault_polygons_provider_factory.create_from_ensemble_fault_polygons_files(
                webviz_settings.shared_settings["scratch_ensembles"][ens]
            )
            for ens in ensembles
        }
        all_fault_polygon_attributes = self._ensemble_fault_polygons_providers[
            ensembles[0]
        ].attributes()
        if (
            fault_polygon_attribute is not None
            and fault_polygon_attribute in all_fault_polygon_attributes
        ):
            self.fault_polygon_attribute = fault_polygon_attribute
        elif all_fault_polygon_attributes:
            self.fault_polygon_attribute = all_fault_polygon_attributes[0]
        else:
            self.fault_polygon_attribute = None

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
            well_names=self.well_pick_provider.well_names()
            if self.well_pick_provider is not None
            else [],
            realizations=reals,
        )

    def set_callbacks(self) -> None:

        plugin_callbacks(
            get_uuid=self.uuid,
            ensemble_surface_providers=self._ensemble_surface_providers,
            surface_server=self._surface_server,
            ensemble_fault_polygons_providers=self._ensemble_fault_polygons_providers,
            fault_polygon_attribute=self.fault_polygon_attribute,
            fault_polygons_server=self._fault_polygons_server,
            map_surface_names_to_fault_polygons=self.map_surface_names_to_fault_polygons,
            well_picks_provider=self.well_pick_provider,
        )
