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

from ._tour_steps import generate_tour_steps
from .controllers import (
    open_dialogs,
    update_intersection,
    update_intersection_source,
    update_maps,
    update_realizations,
    update_uncertainty_table,
)
from .views import (
    clientside_stores,
    dialog,
    intersection_and_map_layout,
    intersection_data_layout,
    map_data_layout,
    realization_layout,
    uncertainty_table_layout,
)


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
        self.set_callbacks(app)

    @property
    def tour_steps(self) -> List[Dict]:
        return generate_tour_steps(get_uuid=self.uuid)

    @property
    def layout(self) -> wcc.FlexBox:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                clientside_stores(
                    get_uuid=self.uuid,
                    realizations=self._realizations,
                    initial_settings=self._initial_settings,
                ),
                wcc.FlexBox(
                    children=[
                        wcc.FlexColumn(
                            wcc.Frame(
                                style={
                                    "height": "91vh",
                                },
                                children=[
                                    html.Div(
                                        children=[
                                            wcc.Selectors(
                                                label="Intersection controls",
                                                children=intersection_data_layout(
                                                    get_uuid=self.uuid,
                                                    surface_attributes=self._surf_attrs,
                                                    surface_names=self._surfacenames,
                                                    ensembles=self.ensembles,
                                                    use_wells=self._use_wells,
                                                    well_names=self._well_set_model.well_names
                                                    if self._well_set_model
                                                    else [],
                                                    surface_geometry=self.first_surface_geometry,
                                                    initial_settings=self._initial_settings.get(
                                                        "intersection_data", {}
                                                    ),
                                                ),
                                            ),
                                            html.Div(
                                                id=self.uuid(
                                                    "surface-settings-wrapper"
                                                ),
                                                children=wcc.Selectors(
                                                    label="Map controls",
                                                    children=[
                                                        map_data_layout(
                                                            uuid=self.uuid(
                                                                "map-settings"
                                                            ),
                                                            surface_attributes=self._surf_attrs,
                                                            surface_names=self._surfacenames,
                                                            ensembles=self.ensembles,
                                                            realizations=self._realizations,
                                                            use_wells=self._use_wells,
                                                        )
                                                    ],
                                                ),
                                            ),
                                            wcc.Selectors(
                                                label="Filters",
                                                children=[
                                                    dialog.open_dialog_layout(
                                                        uuid=self.uuid("dialog"),
                                                        dialog_id="realization-filter",
                                                        title="Realization filter",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ),
                        wcc.FlexColumn(
                            flex=6,
                            children=intersection_and_map_layout(get_uuid=self.uuid),
                        ),
                    ]
                ),
                dialog.dialog_layout(
                    uuid=self.uuid("dialog"),
                    dialog_id="color",
                    title="Color settings",
                    size="lg",
                    children=[
                        html.Div(
                            children=[self._color_picker.layout],
                        ),
                    ],
                ),
                dialog.dialog_layout(
                    uuid=self.uuid("dialog"),
                    dialog_id="realization-filter",
                    title="Filter realizations",
                    children=[
                        realization_layout(
                            uuid=self.uuid("intersection-data"),
                            realizations=self._realizations,
                            value=self._initial_settings.get(
                                "intersection_data", {}
                            ).get("realizations", self._realizations),
                        ),
                        dialog.clear_all_apply_dialog_buttons(
                            uuid=self.uuid("dialog"), dialog_id="realization-filter"
                        ),
                    ],
                ),
                dialog.dialog_layout(
                    uuid=self.uuid("dialog"),
                    dialog_id="uncertainty-table",
                    title="Uncertainty table",
                    children=[
                        uncertainty_table_layout(
                            uuid=self.uuid("uncertainty-table"),
                        )
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        open_dialogs(app=app, get_uuid=self.uuid)
        update_realizations(app=app, get_uuid=self.uuid)
        update_intersection(
            app=app,
            get_uuid=self.uuid,
            surface_set_models=self._surface_ensemble_set_model,
            well_set_model=self._well_set_model,
            zonelog=self._zonelog,
            color_picker=self._color_picker,
        )
        update_maps(
            app=app,
            get_uuid=self.uuid,
            surface_set_models=self._surface_ensemble_set_model,
            well_set_model=self._well_set_model,
        )
        update_uncertainty_table(
            app=app,
            get_uuid=self.uuid,
            surface_set_models=self._surface_ensemble_set_model,
            well_set_model=self._well_set_model,
        )
        update_intersection_source(
            app=app, get_uuid=self.uuid, surface_geometry=self.first_surface_geometry
        )

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
