from typing import Optional, Dict, List

import dash
from dash import Dash, callback, Output, Input, State
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers import SurfaceServer, \
    FaultPolygonsServer
from webviz_subsurface.plugins._co2_leakage._utilities.co2volume import generate_co2_volume_figure, \
    generate_co2_time_containment_figure
from webviz_subsurface.plugins._co2_leakage._utilities.formation_alias import surface_name_aliases, \
    lookup_surface_alias, lookup_fault_polygon_alias, lookup_well_pick_alias
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import property_origin, \
    SurfaceData, derive_surface_address, readable_name, get_plume_polygon, \
    create_map_layers, extract_fault_polygon_url
from webviz_subsurface.plugins._co2_leakage._utilities.general import \
    fmu_realization_paths, first_existing_fmu_file_path, MapAttribute
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import \
    init_map_attribute_names, init_surface_providers, init_fault_polygon_providers, \
    init_well_pick_providers
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import MainView, \
    MapViewElement, INITIAL_BOUNDS
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings

ENSEMBLE_PLOT_HEIGHT = 300
ENSEMBLE_PLOT_WIDTH = 400


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

        # TODO: get rid of stores?
        DATE_STORE = "date-store"
        COLOR_STORE = "color-store"
        PLUME_STORE = "plume-store"

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        boundary_relpath: Optional[str] = "share/results/polygons/leakage_boundary.csv",
        well_pick_relpath: Optional[str] = "share/results/wells/well_picks.csv",
        co2_containment_relpath: Optional[str] = "share/results/tables/co2_volumes.csv",
        fault_polygon_attribute: Optional[str] = "dl_extracted_faultlines",
        map_attribute_names: Optional[Dict[str, str]] = None,
        formation_aliases: Optional[List[List[str]]] = None,
    ):
        super().__init__()
        self.add_shared_settings_group(ViewSettings(ensembles), self.Ids.MAIN_SETTINGS)
        self.add_view(MainView(), self.Ids.MAIN_VIEW)
        self.add_store(self.Ids.DATE_STORE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(self.Ids.COLOR_STORE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(self.Ids.PLUME_STORE, WebvizPluginABC.StorageType.SESSION)

        self._ensemble_paths = webviz_settings.shared_settings["scratch_ensembles"]
        self._map_attribute_names = init_map_attribute_names(map_attribute_names)
        # Surfaces
        self._ensemble_surface_providers = init_surface_providers(
            webviz_settings, ensembles
        )
        self._surface_server = SurfaceServer.instance(app)
        # Polygons
        self._ensemble_fault_polygons_providers = init_fault_polygon_providers(
            webviz_settings, ensembles
        )
        self._polygons_server = FaultPolygonsServer.instance(app)
        for provider in self._ensemble_fault_polygons_providers.values():
            self._polygons_server.add_provider(provider)
        self._formation_aliases = [set(f) for f in formation_aliases or []]
        self._fault_polygon_attribute = fault_polygon_attribute
        # License boundary
        self._boundary_rel_path = boundary_relpath
        # Well picks
        self._well_pick_providers = init_well_pick_providers(
            self._ensemble_paths, well_pick_relpath
        )
        # CO2 containment
        self._co2_containment_relpath = co2_containment_relpath

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
        # TODO:
        #  - many of the callbacks can probably be moved to settings. Is that clearer?

        @callback(
            Output(self._settings_component(ViewSettings.Ids.REALIZATION), "options"),
            Output(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def set_realizations(ensemble):
            rz_paths = fmu_realization_paths(self._ensemble_paths[ensemble])
            realizations = [
                dict(label=r, value=r)
                for r in sorted(rz_paths.keys())
            ]
            fig_args = (
                rz_paths,
                ENSEMBLE_PLOT_HEIGHT,
                ENSEMBLE_PLOT_WIDTH,
                self._co2_containment_relpath,
            )
            fig0 = generate_co2_volume_figure(*fig_args)
            fig1 = generate_co2_time_containment_figure(*fig_args)
            return realizations, [realizations[0]["value"]], fig0, fig1

        @callback(
            Output(self._settings_component(ViewSettings.Ids.FORMATION), 'options'),
            Output(self._settings_component(ViewSettings.Ids.FORMATION), 'value'),
            State(self._settings_component(ViewSettings.Ids.ENSEMBLE), 'value'),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), 'value'),
            State(self._settings_component(ViewSettings.Ids.FORMATION), 'value'),
        )
        def set_formations(ensemble, prop, current_value):
            if ensemble is None:
                return [], None
            surface_provider = self._ensemble_surface_providers[ensemble]
            # Map
            prop_name = property_origin(MapAttribute(prop), self._map_attribute_names)
            surfaces = surface_name_aliases(surface_provider, prop_name)
            # Formation names
            formations = [{"label": v.title(), "value": v} for v in surfaces]
            picked_formation = None
            if len(formations) != 0:
                if any(fmt["value"] == current_value for fmt in formations):
                    picked_formation = dash.no_update
                else:
                    picked_formation = formations[0]["value"]
            return formations, picked_formation

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
            Output(self._settings_component(ViewSettings.Ids.STATISTIC), "disabled"),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
        )
        def toggle_statistics(realizations, attribute):
            if len(realizations) <= 1:
                return True
            elif MapAttribute(attribute) in (
                    MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME
            ):
                return True
            return False

        @callback(
            Output(self.get_store_unique_id(self.Ids.COLOR_STORE), "data"),
            Output(self._settings_component(ViewSettings.Ids.CM_MIN), "disabled"),
            Output(self._settings_component(ViewSettings.Ids.CM_MAX), "disabled"),
            Input(self._settings_component(ViewSettings.Ids.CM_MIN_AUTO), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MIN), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MAX_AUTO), "value"),
            Input(self._settings_component(ViewSettings.Ids.CM_MAX), "value"),
        )
        def set_color_range_data(min_auto, min_val, max_auto, max_val):
            return (
                [
                    min_val if len(min_auto) == 0 else None,
                    max_val if len(max_auto) == 0 else None,
                ],
                len(min_auto) == 1,
                len(max_auto) == 1,
            )

        @callback(
            Output(self.get_store_unique_id(self.Ids.PLUME_STORE), "data"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
            Input(self._settings_component(ViewSettings.Ids.PLUME_THRESHOLD), "value"),
            Input(self._settings_component(ViewSettings.Ids.PLUME_SMOOTHING), "value"),
        )
        def set_plume_contour_data(
                attribute,
                threshold,
                smoothing,
        ):
            if attribute is None:
                return None
            attribute = MapAttribute(attribute)
            if attribute not in (MapAttribute.SGAS_PLUME, MapAttribute.AMFG_PLUME):
                return None
            return {
                "property": property_origin(attribute, self._map_attribute_names),
                "threshold": threshold,
                "smoothing": smoothing,
            }

        @callback(
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "layers"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
            Input(self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"),
            Input(self._settings_component(ViewSettings.Ids.FORMATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.STATISTIC), "value"),
            Input(self._settings_component(ViewSettings.Ids.COLOR_SCALE), "value"),
            Input(self.get_store_unique_id(self.Ids.COLOR_STORE), "data"),
            Input(self.get_store_unique_id(self.Ids.PLUME_STORE), "data"),
            State(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
            State(self.get_store_unique_id(self.Ids.DATE_STORE), "data"),
            State(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
        )
        def update_map_attribute(
                attribute,
                date,
                formation,
                realization,
                statistic,
                color_map_name,
                color_map_range,
                contour_data,
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
            # Look up formation aliases
            surface_name = lookup_surface_alias(
                self._formation_aliases,
                formation,
                self._ensemble_surface_providers[ensemble],
                property_origin(attribute, self._map_attribute_names),
            )
            polygon_name = lookup_fault_polygon_alias(
                self._formation_aliases,
                formation,
                self._ensemble_fault_polygons_providers[ensemble],
                self._fault_polygon_attribute,
            )
            well_pick_horizon = lookup_well_pick_alias(
                self._formation_aliases,
                formation,
                self._well_pick_providers[ensemble],
            )
            # Surface
            if surface_name is None:
                surf_data = None
            elif len(realization) == 0:
                surf_data = None
            else:
                surf_data = SurfaceData.from_server(
                    server=self._surface_server,
                    provider=self._ensemble_surface_providers[ensemble],
                    address=derive_surface_address(
                        surface_name,
                        attribute,
                        date,
                        realization,
                        self._map_attribute_names,
                        statistic,
                        contour_data,
                    ),
                    color_map_range=color_map_range,
                    color_map_name=color_map_name,
                    readable_name=readable_name(attribute),
                )
            # Plume polygon
            plume_polygon = None
            if contour_data is not None:
                plume_polygon = get_plume_polygon(
                    self._ensemble_surface_providers[ensemble],
                    realization,
                    surface_name,
                    date,
                    contour_data,
                )
            # Create layers and view bounds
            layers, viewport_bounds = create_map_layers(
                surface_data=surf_data,
                fault_polygon_url=extract_fault_polygon_url(
                    server=self._polygons_server,
                    provider=self._ensemble_fault_polygons_providers[ensemble],
                    polygon_name=polygon_name,
                    realization=realization,
                    fault_polygon_attribute=self._fault_polygon_attribute,
                ),
                license_boundary_file=first_existing_fmu_file_path(
                    self._ensemble_paths[ensemble], realization, self._boundary_rel_path
                ),
                well_pick_provider=self._well_pick_providers[ensemble],
                well_pick_horizon=well_pick_horizon,
                plume_extent_data=plume_polygon,
            )
            if (
                tuple(current_bounds) != INITIAL_BOUNDS
                or viewport_bounds is None
            ):
                viewport_bounds = dash.no_update
            return layers, viewport_bounds
