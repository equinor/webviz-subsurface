from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers import (
    EnsembleFaultPolygonsProviderFactory,
    EnsembleSurfaceProviderFactory,
)
from webviz_subsurface._providers.ensemble_fault_polygons_provider.fault_polygons_server import (
    FaultPolygonsServer,
)
from webviz_subsurface._providers.ensemble_surface_provider.surface_server import (
    SurfaceServer,
)
from webviz_subsurface._utils.webvizstore_functions import read_csv

from ._tmp_well_pick_provider import WellPickProvider
from .callbacks import plugin_callbacks
from .layout import main_layout


class MapViewerFMU(WebvizPluginABC):
    """Surface visualizer for FMU ensembles.
A dashboard to covisualize arbitrary surfaces generated by FMU.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`attributes`:** List of surface attributes to include, if not given
    all surface attributes will be included.
* **`well_pick_file`:** A csv file with well picks.  See data input.
* **`fault_polygon_attribute`:** Which set of fault polygons to use.
* **`map_surface_names_to_well_pick_names`:** Allows mapping of file surface names
    to the relevant well pick name
* **`map_surface_names_to_fault_polygons`:** Allows mapping of file surface names
    to the relevant fault polygon set name

---
The available maps are gathered from the `share/results/maps/` folder
for each realization. Subfolders are not supported.

Observed maps are gathered from the `share/observations/maps/` folder in the case folder.
The filenames need to follow a fairly strict convention, as the filenames are used as metadata:
`horizon_name--attribute--date` (`--date` is optional). The files should be on `irap binary`
format with the suffix `.gri`. The date is of the form `YYYYMMDD` or
`YYYYMMDD_YYYYMMDD`, the latter would be for a delta surface between two dates.

See [this folder]\
(https://github.com/equinor/webviz-subsurface-testdata/tree/master/01_drogon_ahm/\
realization-0/iter-0/share/results/maps) \
for examples of file naming conventions.

Fault polygons are gathered from the `share/results/polygons` folder for each realization.
Same file naming convention as for surfaces must be folloewed and the suffix should be `.pol`,
representing XYZ format usable by xtgeo.

Well picks are provided as a csv file with columns `X_UTME,Y_UTMN,Z_TVDSS,MD,WELL,HORIZON`.
See [wellpicks.csv](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
    observed_data/drogon_well_picks/wellpicks.csv) for an example.
Well picks can be exported from RMS using this script: [extract_well_picks_from_rms.py]\
    (https://github.com/equinor/webviz-subsurface-testdata/tree/master/observed_data/\
        drogon_well_picks/extract_well_picks_from_rms.py)
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        attributes: list = None,
        well_pick_file: Path = None,
        fault_polygon_attribute: Optional[str] = None,
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
        self.well_pick_file = well_pick_file
        if self.well_pick_file is not None:
            well_pick_table = read_csv(self.well_pick_file)
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
        self.fault_polygon_attribute: Optional[str] = None
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

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions = []
        if self.well_pick_file is not None:
            store_functions.append((read_csv, [{"csv_file": self.well_pick_file}]))
        return store_functions
