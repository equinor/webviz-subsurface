from typing import Optional, Dict, List

import dash
from dash import Dash, callback, Output, Input, State
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers import SurfaceServer, \
    FaultPolygonsServer
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import generate_co2_volume_figure, \
    generate_co2_time_containment_figure
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import property_origin, \
    SurfaceData, derive_surface_address, readable_name, get_plume_polygon, \
    create_map_layers
from webviz_subsurface.plugins._co2_leakage._utilities.fault_polygons import \
    FaultPolygonsHandler
from webviz_subsurface.plugins._co2_leakage._utilities.generic import \
    fmu_realization_paths, first_existing_fmu_file_path, MapAttribute
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import \
    init_map_attribute_names, init_surface_providers, init_well_pick_providers
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import MainView, \
    MapViewElement, INITIAL_BOUNDS
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings


from . import _error


class CO2Leakage(WebvizPluginABC):
    """
    Plugin for analyzing CO2 leakage potential across multiple realizations in an FMU
    ensemble

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`boundary_relpath`:** Path to a polygon representing the containment area
    * **`well_pick_relpath`:** Path to a file containing well picks
    * **`co2_containment_relpath`:** Path to a table of co2 containment data (amount of
        CO2 outside/inside a boundary)
    * **`fault_polygon_attribute`:** Polygons with this attribute are used as fault
        polygons
    * **`map_attribute_names`:** Dictionary for overriding the default mapping between
        attributes visualized by the plugin, and the attributes names used by
        EnsembleSurfaceProvider
    * **`formation_aliases`:** List of formation aliases. Relevant when the formation
        name convention of e.g. well picks is different from that of surface maps

    ---

    TODO: Elaborate on arguments above
    """
    class Ids:
        MAIN_VIEW = "main-view"
        MAIN_SETTINGS = "main-settings"
        DATE_STORE = "date-store"

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        boundary_relpath: str = "share/results/polygons/leakage_boundary.csv",
        well_pick_relpath: str = "share/results/wells/well_picks.csv",
        co2_containment_relpath: str = "share/results/tables/co2_volumes.csv",
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._error_message = ""

        self._co2_containment_relpath = co2_containment_relpath
        self._boundary_rel_path = boundary_relpath
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
            # Well picks
            self._well_pick_providers = init_well_pick_providers(
                self._ensemble_paths,
                well_pick_relpath,
                map_surface_names_to_well_pick_names,
            )
        except Exception as e:
            self._error_message = f"Plugin initialization failed: {e}"

        self.add_shared_settings_group(
            ViewSettings(
                self._ensemble_paths,
                self._ensemble_surface_providers,
                self._map_attribute_names,
            ),
            self.Ids.MAIN_SETTINGS
        )
        self.add_view(MainView(), self.Ids.MAIN_VIEW)
        self.add_store(self.Ids.DATE_STORE, WebvizPluginABC.StorageType.SESSION)

    @property
    def layout(self):
        return _error.error(self._error_message)

    def _view_component(self, component_id):
        return (
            self.view(self.Ids.MAIN_VIEW)
            .view_element(MainView.Ids.MAIN_ELEMENT)
            .component_unique_id(component_id)
            .to_string()
        )

    def _settings_component(self, component_id):
        return (
            self.shared_settings_group(self.Ids.MAIN_SETTINGS)
            .component_unique_id(component_id)
            .to_string()
        )

    def _set_callbacks(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def update_graphs(ensemble):
            rz_paths = fmu_realization_paths(self._ensemble_paths[ensemble])
            fig_args = (
                rz_paths,
                self._co2_containment_relpath,
            )
            fig0 = generate_co2_volume_figure(*fig_args)
            fig1 = generate_co2_time_containment_figure(*fig_args)
            return fig0, fig1

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), 'marks'),
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), 'value'),
            Output(self.get_store_unique_id(self.Ids.DATE_STORE), "data"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), 'value'),
        )
        def set_dates(ensemble):
            if ensemble is None:
                return [], None, []
            # Dates
            surface_provider = self._ensemble_surface_providers[ensemble]
            att_name = self._map_attribute_names[MapAttribute.MAX_SGAS]
            date_list = surface_provider.surface_dates_for_attribute(att_name)
            if date_list is None:
                dates = {}
                initial_date = dash.no_update
            else:
                dates = {
                    i: {
                        "label": f"{d[:4]}",
                        "style": {"writingMode": "vertical-rl"},
                    }
                    for i, d in enumerate(date_list)
                }
                initial_date = max(dates.keys())
            return dates, initial_date, date_list

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
        )
        def toggle_date_slider(attribute):
            if MapAttribute(attribute) == MapAttribute.MIGRATION_TIME:
                return {"display": "none"}
            else:
                return {}

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
            State(self.get_store_unique_id(self.Ids.DATE_STORE), "data"),
            State(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
        )
        def update_map_attribute(
                attribute: str,
                date,
                formation: str,
                realization: List[int],
                statistic: str,
                color_map_name,
                cm_min_auto,
                cm_min_val,
                cm_max_auto,
                cm_max_val,
                plume_threshold,
                plume_smoothing,
                ensemble,
                date_list,
                current_bounds,
        ):
            attribute = MapAttribute(attribute)
            if len(realization) == 0:
                raise PreventUpdate
            if ensemble is None:
                raise PreventUpdate
            if attribute != MapAttribute.MIGRATION_TIME and date is None:
                raise PreventUpdate
            date = str(date_list[date])
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
                color_map_range = (
                    cm_min_val if len(cm_min_auto) == 0 else None,
                    cm_max_val if len(cm_max_auto) == 0 else None,
                )
                surf_data = SurfaceData.from_server(
                    server=self._surface_server,
                    provider=self._ensemble_surface_providers[ensemble],
                    address=derive_surface_address(
                        formation,
                        attribute,
                        date,
                        realization,
                        self._map_attribute_names,
                        statistic,
                        contour_data,
                    ),
                    color_map_range=color_map_range,
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
                    date,
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
                license_boundary_file=first_existing_fmu_file_path(
                    self._ensemble_paths[ensemble], realization, self._boundary_rel_path
                ),
                well_pick_provider=self._well_pick_providers.get(ensemble, None),
                plume_extent_data=plume_polygon,
            )
            if (
                tuple(current_bounds) != INITIAL_BOUNDS
                or viewport_bounds is None
            ):
                viewport_bounds = dash.no_update
            return layers, viewport_bounds
