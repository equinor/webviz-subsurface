from typing import Dict, List

from dash import Dash
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProvider,
    EnsembleGridProviderFactory,
    GridVizService,
)

from ._layout_elements import ElementIds
from ._routes import set_routes
from .views.view_3d._view_3d import View3D


class EXPERIMENTALGridViewerFMU(WebvizPluginABC):
    """
    !> This plugin is an experimental plugin and will see significant changes
    in the future. It is not recommended to use this plugin in a cloud setting.
    There might be unexpected issues and errors in the visualization. Results
    should be validated in ResInsight/RMS!

    The plugin allows for basic visualization of 3D grids and properties
    from FMU ensembles.

    The performance is related to the number of cells,
    and will probably not handle large modelling grids (10+ million cells) at all.

    ---
    * **`ensemble`:** Which ensemble in `shared_settings` to include.

    Provide the grid data either as ROFF:
    * **`roff_grid_name`:** Name of roff grid stored in FMU standard.
    * **`roff_attribute_filter`:** Use an optional subset of roff grid parameters

    Or as Eclipse:
    * **`eclipse_grid_name`:** Case name of the Eclipse files
    * **`eclipse_init_parameters`:** Which Eclipse init parameters to load
    * **`eclipse_restart_parameters`:** Which Eclipse restart parameters to load

    An optional initial cell filter can be set as:
    * **`grid_ijk_filter`:** with one or more of the following:
        ```yaml
            i_min: start column
            i_width: number of columns
            j_min: start row
            j_width: number of rows
            k_min: start layer
            k_width: number of layers
        ```

    ---
    Data can be loaded either from an Eclipse simulation case or from roff files.

    For Eclipse simulations provide the case name as `eclipse_grid_name`, together
    with a list of `eclipse_init_parameters` and `eclipse_restart_parameters`.
    The plugin will then load from the corresponding EGRID, INIT and UNRST files
    in the `eclipse/model` folder.

    For grids stored in ROFF format, the FMU standards are followed. Provide
    a `roff_grid_name` together with an optional `roff_attribute_filter`.
    The corresponding files are then loaded from the `share/results/grids` folder.

    Note that the ROFF format is recommended for best performance.


    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensemble: str,
        roff_grid_name: str = None,
        roff_attribute_filter: List[str] = None,
        eclipse_grid_name: str = None,
        eclipse_init_parameters: List[str] = None,
        eclipse_restart_parameters: List[str] = None,
        initial_ijk_filter: Dict[str, int] = None,
    ):

        super().__init__(stretch=True)

        self.ensemble = webviz_settings.shared_settings["scratch_ensembles"][ensemble]

        if roff_grid_name:
            self.add_roff_grid_provider(
                grid_name=roff_grid_name, attribute_filter=roff_attribute_filter
            )
        elif (
            eclipse_grid_name and eclipse_init_parameters and eclipse_restart_parameters
        ):
            self.add_eclipse_grid_provider(
                grid_name=eclipse_grid_name,
                init_properties=eclipse_init_parameters,
                restart_properties=eclipse_restart_parameters,
            )
        else:
            raise ValueError(
                "Either provide roff_grid_name or "
                "eclipse_grid_name, eclipse_init_parameters and eclipse_restart_parameters"
            )
        self.add_store(
            ElementIds.IJK_CROP_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )

        self.add_view(
            View3D(
                grid_provider=self.grid_provider,
                grid_viz_service=self.grid_viz_service,
                initial_grid_filter=initial_ijk_filter if initial_ijk_filter else {},
            ),
            ElementIds.ID,
        )
        try:
            set_routes(app, self.grid_viz_service)
        except AssertionError:
            pass

    def add_roff_grid_provider(
        self, grid_name: str, attribute_filter: List[str] = None
    ) -> None:
        factory = EnsembleGridProviderFactory.instance()

        self.grid_provider: EnsembleGridProvider = factory.create_from_roff_files(
            ens_path=self.ensemble,
            grid_name=grid_name,
            attribute_filter=attribute_filter,
        )
        self.grid_viz_service = GridVizService.instance()
        self.grid_viz_service.register_provider(self.grid_provider)

    def add_eclipse_grid_provider(
        self, grid_name: str, init_properties: List[str], restart_properties: List[str]
    ) -> None:
        factory = EnsembleGridProviderFactory.instance()
        self.grid_provider = factory.create_from_eclipse_files(
            ens_path=self.ensemble,
            grid_name=grid_name,
            init_properties=init_properties,
            restart_properties=restart_properties,
        )
        self.grid_viz_service = GridVizService.instance()
        self.grid_viz_service.register_provider(self.grid_provider)
