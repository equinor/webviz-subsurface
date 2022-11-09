from typing import Any, Dict, List, Optional, Tuple

import dash
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._providers import FaultPolygonsServer, SurfaceServer
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import (
    SurfaceData,
    create_map_layers,
    derive_surface_address,
    get_plume_polygon,
    property_origin,
    readable_name,
)
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import (
    generate_co2_time_containment_figure,
    generate_co2_volume_figure,
)
from webviz_subsurface.plugins._co2_leakage._utilities.fault_polygons import (
    FaultPolygonsHandler,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import MapAttribute
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import (
    init_co2_containment_table_providers,
    init_map_attribute_names,
    init_surface_providers,
    init_well_pick_provider,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import (
    INITIAL_BOUNDS,
    MainView,
    MapViewElement,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings

from . import _error
from ._utilities.color_tables import CO2LEAKAGE_COLOR_TABLES


class CO2Leakage(WebvizPluginABC):
    """
    Plugin for analyzing CO2 leakage potential across multiple realizations in an FMU
    ensemble

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`boundary_file`:** Path to a polygon representing the containment area
    * **`well_pick_file`:** Path to a file containing well picks
    * **`co2_containment_relpath`:** Path to a table of co2 containment data (amount of
        CO2 outside/inside a boundary). Relative to each realization.
    * **`fault_polygon_attribute`:** Polygons with this attribute are used as fault
        polygons
    * **`map_attribute_names`:** Dictionary for overriding the default mapping between
        attributes visualized by the plugin and attributes names used by
        EnsembleSurfaceProvider
    * **`initial_surface`:** Name of the surface/formation to show when the plugin is
        launched. If no name is provided, the first alphabetical surface is shown.
    * **`map_surface_names_to_well_pick_names`:** Optional mapping between surface map
        names and surface names used in the well pick file
    * **`map_surface_names_to_fault_polygons`:** Optional mapping between surface map
        names and surface names used by the fault polygons
    """

    class Ids(StrEnum):
        MAIN_VIEW = "main-view"
        MAIN_SETTINGS = "main-settings"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        boundary_file: Optional[str] = None,
        well_pick_file: Optional[str] = None,
        co2_containment_relpath: str = "share/results/tables/co2_volumes.csv",
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        initial_surface: Optional[str] = None,
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._error_message = ""

        self._boundary_file = boundary_file
        try:
            self._ensemble_paths = webviz_settings.shared_settings["scratch_ensembles"]
            self._surface_server = SurfaceServer.instance(app)
            self._polygons_server = FaultPolygonsServer.instance(app)

            self._map_attribute_names = init_map_attribute_names(map_attribute_names)
            # Surfaces
            self._ensemble_surface_providers = init_surface_providers(
                webviz_settings, ensembles
            )
            # Polygons
            self._fault_polygon_handlers = {
                ens: FaultPolygonsHandler(
                    self._polygons_server,
                    self._ensemble_paths[ens],
                    map_surface_names_to_fault_polygons or {},
                    fault_polygon_attribute,
                )
                for ens in ensembles
            }
            # CO2 containment
            self._co2_table_providers = init_co2_containment_table_providers(
                self._ensemble_paths,
                co2_containment_relpath,
            )
            # Well picks
            self._well_pick_provider = init_well_pick_provider(
                well_pick_file,
                map_surface_names_to_well_pick_names,
            )
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

        self.add_shared_settings_group(
            ViewSettings(
                self._ensemble_paths,
                self._ensemble_surface_providers,
                initial_surface,
                self._map_attribute_names,
                [c["name"] for c in CO2LEAKAGE_COLOR_TABLES],  # type: ignore
            ),
            self.Ids.MAIN_SETTINGS,
        )
        self.add_view(MainView(CO2LEAKAGE_COLOR_TABLES), self.Ids.MAIN_VIEW)

    @property
    def layout(self) -> html.Div:
        return _error.error(self._error_message)

    def _view_component(self, component_id: str) -> str:
        return (
            self.view(self.Ids.MAIN_VIEW)
            .view_element(MainView.Ids.MAIN_ELEMENT)
            .component_unique_id(component_id)
            .to_string()
        )

    def _settings_component(self, component_id: str) -> str:
        return (
            self.shared_settings_group(self.Ids.MAIN_SETTINGS)
            .component_unique_id(component_id)
            .to_string()
        )

    def _ensemble_dates(self, ens: str) -> List[str]:
        surface_provider = self._ensemble_surface_providers[ens]
        att_name = self._map_attribute_names[MapAttribute.MAX_SGAS]
        dates = surface_provider.surface_dates_for_attribute(att_name)
        if dates is None:
            raise ValueError(f"Failed to fetch dates for attribute '{att_name}'")
        return dates

    def _set_callbacks(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def update_graphs(ensemble: str) -> Tuple[go.Figure, go.Figure]:
            fig_args = (
                self._co2_table_providers[ensemble],
                self._co2_table_providers[ensemble].realizations(),
            )
            fig0 = generate_co2_volume_figure(*fig_args)
            fig1 = generate_co2_time_containment_figure(*fig_args)
            return fig0, fig1

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), "marks"),
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def set_dates(ensemble: str) -> Tuple[Dict[int, Dict[str, Any]], Optional[int]]:
            if ensemble is None:
                return {}, None
            # Dates
            date_list = self._ensemble_dates(ensemble)
            dates = {
                i: {
                    "label": f"{d[:4]}",
                    "style": {"writingMode": "vertical-rl"},
                }
                for i, d in enumerate(date_list)
            }
            initial_date = max(dates.keys())
            return dates, initial_date

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
        )
        def toggle_date_slider(attribute: str) -> Dict[str, str]:
            if MapAttribute(attribute) == MapAttribute.MIGRATION_TIME:
                return {"display": "none"}
            return {}

        # Cannot avoid many arguments and/or locals since all layers of the DeckGL map
        # needs to be updated simultaneously
        # pylint: disable=too-many-arguments,too-many-locals
        @callback(
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "layers"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
            Input(self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"),
            Input(self._settings_component(ViewSettings.Ids.FORMATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.STATISTIC), "value"),
            Input(self._settings_component(ViewSettings.Ids.COLOR_SCALE), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MIN_AUTO), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MIN), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MAX_AUTO), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MAX), "value"),
            Input(self._settings_component(ViewSettings.Ids.PLUME_THRESHOLD), "value"),
            Input(self._settings_component(ViewSettings.Ids.PLUME_SMOOTHING), "value"),
            State(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
            State(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
        )
        def update_map_attribute(
            attribute: MapAttribute,
            date: int,
            formation: str,
            realization: List[int],
            statistic: str,
            color_map_name: str,
            cm_min_auto: List[str],
            cm_min_val: Optional[float],
            cm_max_auto: List[str],
            cm_max_val: Optional[float],
            plume_threshold: Optional[float],
            plume_smoothing: Optional[float],
            ensemble: str,
            current_bounds: List[float],
        ) -> Tuple[List[Dict[str, Any]], Optional[List[float]]]:
            attribute = MapAttribute(attribute)
            if len(realization) == 0:
                raise PreventUpdate
            if ensemble is None:
                raise PreventUpdate
            datestr = self._ensemble_dates(ensemble)[date]
            # Contour data
            contour_data = None
            if attribute in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
                contour_data = {
                    "property": property_origin(attribute, self._map_attribute_names),
                    "threshold": plume_threshold,
                    "smoothing": plume_smoothing,
                }
            # Surface
            surf_data = None
            if formation is not None and len(realization) > 0:
                surf_data = SurfaceData.from_server(
                    server=self._surface_server,
                    provider=self._ensemble_surface_providers[ensemble],
                    address=derive_surface_address(
                        formation,
                        attribute,
                        datestr,
                        realization,
                        self._map_attribute_names,
                        statistic,
                        contour_data,
                    ),
                    color_map_range=(
                        cm_min_val if len(cm_min_auto) == 0 else None,
                        cm_max_val if len(cm_max_auto) == 0 else None,
                    ),
                    color_map_name=color_map_name,
                    readable_name_=readable_name(attribute),
                )
            # Plume polygon
            plume_polygon = None
            if contour_data is not None:
                plume_polygon = get_plume_polygon(
                    self._ensemble_surface_providers[ensemble],
                    realization,
                    formation,
                    datestr,
                    contour_data,
                )
            # Create layers and view bounds
            layers, viewport_bounds = create_map_layers(
                formation=formation,
                surface_data=surf_data,
                fault_polygon_url=(
                    self._fault_polygon_handlers[ensemble].extract_fault_polygon_url(
                        formation,
                        realization,
                    )
                ),
                license_boundary_file=self._boundary_file,
                well_pick_provider=self._well_pick_provider,
                plume_extent_data=plume_polygon,
            )
            if tuple(current_bounds) != INITIAL_BOUNDS or viewport_bounds is None:
                viewport_bounds = dash.no_update
            return layers, viewport_bounds
