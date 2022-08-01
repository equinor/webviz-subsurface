import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
from webviz_subsurface._components import ColorPicker
from webviz_subsurface._datainput.fmu_input import find_surfaces, get_realizations
from webviz_subsurface._models import SurfaceSetModel, WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files, get_path

# from ._controllers import (
#     open_dialogs,
#     update_intersection,
#     update_intersection_source,
#     update_maps,
#     update_realizations,
#     update_uncertainty_table,
# )
from ._plugin_ids import PluginIds
from ._shared_settings._intersection_controls import IntersectionControls
from ._shared_settings._map_controls import MapControls
from ._tour_steps import generate_tour_steps
from ._views._struct_view import StructView

# from ._views import (
#     clientside_stores,
#     dialog,
#     intersection_and_map_layout,
#     intersection_data_layout,
#     map_data_layout,
#     realization_layout,
#     uncertainty_table_layout,
# )


class StructuralUncertainty(WebvizPluginABC):
    """Dashboard to analyze structural uncertainty results from FMU runs.

A cross-section along a well or from a polyline drawn interactively on a map.
Map views to compare two surfaces from e.g. two iterations.

Both individual realization surfaces and statistical surfaces can be plotted.

Wells are required. If a zonelog is provided formation tops are extracted
and plotted as markers along the well trajectory.

Customization of colors and initialization of plugin with predefined selections
is possible. See the `Arguments` sections for details.

!> This plugin follows the FMU standards for storing and naming surface files.
Surface files must be stored at `share/results/maps` for each ensemble,
and be named as `surfacename--surfaceattribute.gri`

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`surface_attributes`:** List of surface attributes from surface filenames(FMU standard). \
All surface_attributes must have the same surface names.
 * **`surface_name_filter`:** List of the surface names (FMU standard) in stratigraphic order
* **`wellfolder`:** A folder with wells on RMS Well format. \
(absolute or relative to config file).
* **`wellsuffix`:** File suffix for wells in `wellfolder`.
* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).
* **`mdlog`:** Name of mdlog in `wellfiles` (displayed along well trajectory).
* **`well_tvdmin`:** Truncate well trajectory values above this depth.
* **`well_tvdmax`:** Truncate well trajectory values below this depth.
* **`well_downsample_interval`:** Sampling interval used for coarsening a well trajectory
* **`calculate_percentiles`:** Only relevant for portable. Calculating P10/90 is
time consuming and is by default disabled to allow fast generation of portable apps. \
Activate to precalculate these percentiles for all realizations. \
* **`initial_settings`:** Configuration for initializing the plugin with various \
    properties set. All properties are optional.
    ```yaml
        initial_settings:
            intersection_data: # Data to populate the intersection view
                surface_attribute: ds_extracted_horizons  #name of active attribute
                surface_names: #list of active surfacenames
                    - topupperreek
                    - baselowerreek
                ensembles: #list of active ensembles
                    - iter-0
                    - iter-1
                calculation: #list of active calculations
                    - Mean
                    - Min
                    - Max
                    - Realizations
                    - Uncertainty envelope
                well: OP_6 #Active well
                realizations: #List of active realizations
                    - 0
                resolution: 20 # Horizontal distance between points in the intersection
                             # (Usually in meters)
                extension: 500 # Horizontal extension of the intersection
                depth_truncations: # Truncations to use for yaxis range
                    min: 1500
                    max: 3000
            colors: # Colors to use for surfaces in the intersection view specified
                    # for each ensemble
                topupperreek:
                    iter-0: '#2C82C9' #hex color code with apostrophies and hash prefix
            intersection_layout: # The full plotly layout
                                 # (https://plotly.com/python/reference/layout/) is
                                 # exposed to allow for customization of e.g. plot title
                                 # and axis ranges. A small example:
                yaxis:
                    title: True vertical depth [m]
                xaxis:
                    title: Lateral distance [m]
    ```
---

**Example files**

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/\
maps/topupperreek--ds_extracted_horizons.gri).

* [Wellfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
observed_data/wells).

The surfacefiles are on a `Irap binary` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).
"""

    # pylint: disable=too-many-arguments, too-many-instance-attributes, too-many-locals
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        surface_attributes: list,
        surface_name_filter: List[str] = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        zonelog: str = None,
        mdlog: str = None,
        well_tvdmin: Union[int, float] = None,
        well_tvdmax: Union[int, float] = None,
        well_downsample_interval: int = None,
        calculate_percentiles: bool = False,
        initial_settings: Dict = None,
    ):

        super().__init__()
        self._initial_settings = initial_settings if initial_settings else {}

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "structural_uncertainty.css"
        )
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "clientside_functions.js"
        )
        self._calculate_percentiles = calculate_percentiles
        self._wellfolder = wellfolder
        self._wellsuffix = wellsuffix
        self._wellfiles: List = []
        if wellfolder is not None:
            self._wellfiles = json.load(find_files(wellfolder, wellsuffix))

        self._well_set_model = WellSetModel(
            self._wellfiles,
            zonelog=zonelog,
            mdlog=mdlog,
            tvdmin=well_tvdmin,
            tvdmax=well_tvdmax,
            downsample_interval=well_downsample_interval,
        )
        self._use_wells = bool(self._wellfiles)
        if (
            self._initial_settings.get("intersection_data", {}).get("well")
            and not self._use_wells
        ):
            raise KeyError(
                "Well is specified in initial settings but no well data is found!"
            )
        self._surf_attrs = surface_attributes
        self._ensemble_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        # Create a table of surface files
        surface_table = find_surfaces(self._ensemble_paths)
        # Filter on provided surface attributes
        surface_table = surface_table[surface_table["attribute"].isin(self._surf_attrs)]
        # Filter on provided surface names
        self._surfacenames = (
            list(surface_table["name"].unique())
            if surface_name_filter is None
            else surface_name_filter
        )
        surface_table = surface_table[surface_table["name"].isin(surface_name_filter)]

        if surface_table.empty:
            raise ValueError("No surfaces found with the given attributes")

        self.ensembles = list(surface_table["ENSEMBLE"].unique())
        for _, attr_df in surface_table.groupby("attribute"):

            if set(attr_df["name"].unique()) != set(self._surfacenames):
                raise ValueError(
                    "Surface attributes has different surfaces. This is not supported!"
                )

        self._surface_ensemble_set_model = {
            ens: SurfaceSetModel(surf_ens_df)
            for ens, surf_ens_df in surface_table.groupby("ENSEMBLE")
        }
        self._realizations = sorted(list(surface_table["REAL"].unique()))

        self._zonelog = zonelog
        colors = [
            "#1f77b4",  # muted blue
            "#ff7f0e",  # safety orange
            "#2ca02c",  # cooked asparagus green
            "#d62728",  # brick red
            "#9467bd",  # muted purple
            "#8c564b",  # chestnut brown
            "#e377c2",  # raspberry yogurt pink
            "#7f7f7f",  # middle gray
            "#bcbd22",  # curry yellow-green
            "#17becf",  # blue-teal
        ]
        self._surfacecolors = [
            {
                "surfacename": surfacename,
                "ensemble": ens,
                "COLOR": self._initial_settings.get("colors", {})
                .get(surfacename, {})
                .get(ens, colors[idx % len(colors)]),
            }
            for idx, surfacename in enumerate(self._surfacenames)
            for ens in self.ensembles
        ]
        self._color_picker = ColorPicker(
            app=app,
            uuid=self.uuid("colorpicker"),
            dframe=pd.DataFrame(self._surfacecolors),
        )
        self.first_surface_geometry = self._surface_ensemble_set_model[
            self.ensembles[0]
        ].first_surface_geometry

        # ------------- Stores ------------------

        self.add_store(PluginIds.Stores.SOURCE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.STORED_POLYLINE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.X_LINE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.MAP_STORED_XLINE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.Y_LINE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.MAP_STORED_YLINE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.STEP_X, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.STEP_Y, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.WELL, WebvizPluginABC.StorageType.SESSION)
        self.add_store(
            PluginIds.Stores.SURFACE_ATTR, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_NAMES, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SHOW_SURFACES, WebvizPluginABC.StorageType.SESSION
        )
        # Buttons
        self.add_store(PluginIds.Stores.RESOLUTION, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.EXTENSION, WebvizPluginABC.StorageType.SESSION)
        self.add_store(
            PluginIds.Stores.Z_RANGE_MIN, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.Z_RANGE_MAX, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.TRUNKATE_LOCK, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(PluginIds.Stores.KEEP_ZOOM, WebvizPluginABC.StorageType.SESSION)
        # Button

        # Map Controls
        self.add_store(
            PluginIds.Stores.SURFACE_ATTRIBUTE_A, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_NAME_A, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.CALCULATION_REAL_A, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.CALCULATE_WELL_INTER_A, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_ATTRIBUTE_B, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_NAME_B, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.CALCULATION_REAL_B, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.CALCULATE_WELL_INTER_B, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.AUTO_COMP_DIFF, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.COLOR_RANGES, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_A_MIN, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_A_MAX, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_B_MIN, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SURFACE_B_MAX, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SYNC_RANGE_ON_MAPS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.ENSEMBLES, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.REAL_FILTER, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.REAL_STORE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.INTERSECTION_DATA, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.INIT_INTERSECTION_LAYOUT, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.ENSEMBLE_A, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.ENSEMBLE_B, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.FIRST_CALL, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.INTERSECTION_LAYOUT, WebvizPluginABC.StorageType.SESSION
        )

        # ------------- Shared settings ------------------

        self.add_shared_settings_group(
            IntersectionControls(
                self._surf_attrs,
                self._surfacenames,
                self.ensembles,
                self._use_wells,
                self._well_set_model.well_names,
                self.first_surface_geometry,
                self._initial_settings,
                self._realizations
            ),
            PluginIds.SharedSettings.INTERSECTION_CONTROLS,
        )

        self.add_shared_settings_group(
            MapControls(
                self._surf_attrs,
                self._surfacenames,
                self.ensembles,
                self._realizations,
                self._use_wells,
            ),
            PluginIds.SharedSettings.MAP_CONTROLS,
        )

        # ------------- Views ------------------

        self.add_view(StructView(self._surface_ensemble_set_model, self._well_set_model,self._color_picker , self._zonelog), PluginIds.ViewID.INTERSECT_POLYLINE)
        
    @property
    def tour_steps(self) -> List[Dict]:
        return generate_tour_steps(get_uuid=self.uuid)

    @property
    def layout(self) -> wcc.FlexBox:
        return

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions: List[Tuple[Callable, list]] = []
        if self._use_wells is not None:
            store_functions.extend(
                [(get_path, [{"path": fn}]) for fn in self._wellfiles]
            )

        store_functions.append(
            (
                find_surfaces,
                [
                    {
                        "ensemble_paths": self._ensemble_paths,
                        "suffix": "*.gri",
                        "delimiter": "--",
                    }
                ],
            )
        )
        calculations: List[str] = ["Mean", "StdDev", "Min", "Max"]
        if self._calculate_percentiles:
            calculations.extend(["P10", "P90"])
        for ens in self.ensembles:

            for calculation in calculations:
                store_functions.append(
                    self._surface_ensemble_set_model[
                        ens
                    ].webviz_store_statistical_calculation(calculation=calculation)
                )
            store_functions.append(
                self._surface_ensemble_set_model[
                    ens
                ].webviz_store_realization_surfaces()
            )
        store_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self._ensemble_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        if self._wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self._wellfolder, "suffix": self._wellsuffix}])
            )
        return store_functions
