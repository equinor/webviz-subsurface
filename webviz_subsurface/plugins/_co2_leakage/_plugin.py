from typing import Any, Dict, List, Optional, Tuple, Union

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, html, no_update
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum, callback_typecheck

from webviz_subsurface._providers import FaultPolygonsServer, SurfaceImageServer
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import (
    SurfaceData,
    create_map_annotations,
    create_map_layers,
    create_map_viewports,
    derive_surface_address,
    generate_containment_figures,
    generate_unsmry_figures,
    get_plume_polygon,
    property_origin,
    readable_name,
)
from webviz_subsurface.plugins._co2_leakage._utilities.fault_polygons import (
    FaultPolygonsHandler,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    GraphSource,
    MapAttribute,
    ZoneViews,
)
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import (
    init_map_attribute_names,
    init_surface_providers,
    init_table_provider,
    init_well_pick_provider,
    init_zone_options,
    process_files,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import (
    MainView,
    MapViewElement,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings

from . import _error
from ._utilities.color_tables import co2leakage_color_tables

TILE_PATH = "share/results/tables"


class CO2Leakage(WebvizPluginABC):
    """
    Plugin for analyzing CO2 leakage potential across multiple realizations in an FMU
    ensemble

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`file_containment_boundary`:** Path to a polygon representing the containment area
    * **`file_hazardous_boundary`:** Path to a polygon representing the hazardous area
    * **`well_pick_file`:** Path to a file containing well picks
    * **`plume_mass_relpath`:** Path to a table of co2 containment data (amount of
        CO2 outside/inside a boundary), for co2 mass. Relative to each realization.
    * **`plume_actual_volume_relpath`:** Path to a table of co2 containment data (amount
        of CO2 outside/inside a boundary), for co2 volume of type "actual". Relative to each
        realization.
    * **`unsmry_relpath`:** Relative path to a csv version of a unified summary file
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
    # pylint: disable=too-many-locals
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        file_containment_boundary: Optional[str] = None,
        file_hazardous_boundary: Optional[str] = None,
        well_pick_file: Optional[str] = None,
        plume_mass_relpath: str = TILE_PATH + "/plume_mass.csv",
        plume_actual_volume_relpath: str = TILE_PATH + "/plume_actual_volume.csv",
        unsmry_relpath: str = TILE_PATH + "/unsmry--raw.csv",
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        initial_surface: Optional[str] = None,
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._error_message = ""
        try:
            self._ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }
            # TODO? add support for different polygons and wells for each ensemble
            (
                self._file_containment_boundary,
                self._file_hazardous_boundary,
                well_pick_file,
            ) = process_files(
                file_containment_boundary,
                file_hazardous_boundary,
                well_pick_file,
                list(self._ensemble_paths.values())[0],
            )
            self._surface_server = SurfaceImageServer.instance(app)
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
            self._co2_table_providers = init_table_provider(
                self._ensemble_paths,
                plume_mass_relpath,
            )
            self._co2_actual_volume_table_providers = init_table_provider(
                self._ensemble_paths,
                plume_actual_volume_relpath,
            )
            self._unsmry_providers = init_table_provider(
                self._ensemble_paths,
                unsmry_relpath,
            )
            # Well picks
            self._well_pick_provider = init_well_pick_provider(
                well_pick_file,
                map_surface_names_to_well_pick_names,
            )
            # Zone options
            self._zone_options = init_zone_options(
                self._ensemble_paths,
                self._co2_table_providers,
                self._co2_actual_volume_table_providers,
                self._ensemble_surface_providers,
            )
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

        self._summed_co2 = {}
        self._visualization_threshold = -1
        self._color_tables = co2leakage_color_tables()
        self.add_shared_settings_group(
            ViewSettings(
                self._ensemble_paths,
                self._ensemble_surface_providers,
                initial_surface,
                self._map_attribute_names,
                [c["name"] for c in self._color_tables],  # type: ignore
                self._well_pick_provider.well_names()
                if self._well_pick_provider
                else [],
                self._zone_options,
            ),
            self.Ids.MAIN_SETTINGS,
        )
        self.add_view(MainView(self._color_tables), self.Ids.MAIN_VIEW)

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
            Output(self._settings_component(ViewSettings.Ids.ZONE_VIEW), "value"),
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Output(
                self._view_component(MapViewElement.Ids.TIME_PLOT_ONE_REAL), "figure"
            ),
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "style"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "style"),
            Output(
                self._view_component(MapViewElement.Ids.TIME_PLOT_ONE_REAL), "style"
            ),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
            Input(self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"),
            Input(self._settings_component(ViewSettings.Ids.CO2_SCALE), "value"),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Input(self._settings_component(ViewSettings.Ids.Y_MIN_AUTO_GRAPH), "value"),
            Input(self._settings_component(ViewSettings.Ids.Y_MIN_GRAPH), "value"),
            Input(self._settings_component(ViewSettings.Ids.Y_MAX_AUTO_GRAPH), "value"),
            Input(self._settings_component(ViewSettings.Ids.Y_MAX_GRAPH), "value"),
            Input(self._settings_component(ViewSettings.Ids.ZONE), "value"),
            State(self._settings_component(ViewSettings.Ids.ZONE), "options"),
            Input(self._settings_component(ViewSettings.Ids.ZONE_VIEW), "value"),
        )
        @callback_typecheck
        def update_graphs(
            ensemble: str,
            source: GraphSource,
            co2_scale: Union[Co2MassScale, Co2VolumeScale],
            realizations: List[int],
            y_min_auto: List[str],
            y_min_val: Optional[float],
            y_max_auto: List[str],
            y_max_val: Optional[float],
            zone: Optional[str],
            zones: Optional[List[str]],
            zone_view: str,
        ) -> Tuple[go.Figure, go.Figure, Dict, Dict]:
            styles = [{"display": "none"}] * 3
            figs = [no_update] * 3
            if source in [
                GraphSource.CONTAINMENT_MASS,
                GraphSource.CONTAINMENT_ACTUAL_VOLUME,
            ]:
                if zones:
                    zones = [zn for zn in zones if zn != "all"]
                else:
                    zone_view = ZoneViews.CONTAINMENTSPLIT
                if zone_view == ZoneViews.ZONESPLIT:
                    zone = "zone_per_real"
                y_limits = [
                    y_min_val if len(y_min_auto) == 0 else None,
                    y_max_val if len(y_max_auto) == 0 else None,
                ]
                styles = [{}] * 3

                if (
                    source == GraphSource.CONTAINMENT_MASS
                    and ensemble in self._co2_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_table_providers[ensemble],
                        co2_scale,
                        realizations[0],
                        y_limits,
                        zone,
                        zones,
                    )
                elif (
                    source == GraphSource.CONTAINMENT_ACTUAL_VOLUME
                    and ensemble in self._co2_actual_volume_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_actual_volume_table_providers[ensemble],
                        co2_scale,
                        realizations[0],
                        y_limits,
                        zone,
                        zones,
                    )
                for fig in figs:
                    fig["layout"]["uirevision"] = f"{source}-{co2_scale}-{zone}"
                figs[-1]["layout"]["uirevision"] += f"-{realizations}"
            elif source == GraphSource.UNSMRY and ensemble in self._unsmry_providers:
                u_figs = generate_unsmry_figures(
                    self._unsmry_providers[ensemble],
                    co2_scale,
                    self._co2_table_providers[ensemble],
                )
                figs[: len(u_figs)] = u_figs
                styles[: len(u_figs)] = [{}] * len(u_figs)
            else:
                zone_view = ZoneViews.CONTAINMENTSPLIT
            return zone_view, *figs, *styles  # type: ignore

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

        @callback(
            Output(self._settings_component(ViewSettings.Ids.CO2_SCALE), "options"),
            Output(self._settings_component(ViewSettings.Ids.CO2_SCALE), "value"),
            Input(self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"),
        )
        def make_unit_list(
            attribute: str,
        ) -> Union[
            Tuple[List[Co2MassScale], Co2MassScale],
            Tuple[List[Co2VolumeScale], Co2VolumeScale],
        ]:
            if attribute == GraphSource.CONTAINMENT_ACTUAL_VOLUME:
                return list(Co2VolumeScale), Co2VolumeScale.BILLION_CUBIC_METERS

            return list(Co2MassScale), Co2MassScale.MTONS

        # Cannot avoid many arguments and/or locals since all layers of the DeckGL map
        # needs to be updated simultaneously
        # pylint: disable=too-many-arguments,too-many-locals
        @callback(
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "layers"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "children"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "views"),
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
            Input(
                self._settings_component(ViewSettings.Ids.VISUALIZATION_THRESHOLD),
                "value",
            ),
            Input(
                self._settings_component(ViewSettings.Ids.VISUALIZATION_SHOW_0), "value"
            ),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_OPTIONS, "value"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "value"),
            State(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
            State(self._view_component(MapViewElement.Ids.DECKGL_MAP), "views"),
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
            visualization_threshold: Optional[float],
            visualize_0: List[str],
            options_dialog_options: List[int],
            selected_wells: List[str],
            ensemble: str,
            current_views: List[Any],
        ) -> Tuple[List[Dict[Any, Any]], List[Any], Dict[Any, Any]]:
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
            if len(visualize_0) != 0:
                visualization_threshold = -1
            elif visualization_threshold is None:
                visualization_threshold = 1e-10
            # Clear surface cache if the threshold for visualization is changed
            if self._visualization_threshold != visualization_threshold:
                print("Clearing cache because the visualization threshold was changed")
                print("Re-select realization(s) to update the current map")
                self._surface_server._image_cache.clear()
                self._visualization_threshold = visualization_threshold
            # Surface
            surf_data = None
            summed_mass = None
            if formation is not None and len(realization) > 0:
                surf_data, summed_mass = SurfaceData.from_server(
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
                    visualization_threshold=visualization_threshold,
                )
            summed_co2_key = f"{formation}-{realization[0]}-{datestr}-{attribute}"
            if len(realization) == 1:
                if attribute in [
                    MapAttribute.MASS,
                    MapAttribute.DISSOLVED,
                    MapAttribute.FREE,
                ]:
                    if (
                        summed_mass is not None
                        and summed_co2_key not in self._summed_co2
                    ):
                        self._summed_co2[summed_co2_key] = summed_mass
                    if summed_co2_key in self._summed_co2:
                        surf_data.readable_name += " (Total: {:.2e}): ".format(
                            self._summed_co2[summed_co2_key]
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
            layers = create_map_layers(
                formation=formation,
                surface_data=surf_data,
                fault_polygon_url=(
                    self._fault_polygon_handlers[ensemble].extract_fault_polygon_url(
                        formation,
                        realization,
                    )
                ),
                file_containment_boundary=self._file_containment_boundary,
                file_hazardous_boundary=self._file_hazardous_boundary,
                well_pick_provider=self._well_pick_provider,
                plume_extent_data=plume_polygon,
                options_dialog_options=options_dialog_options,
                selected_wells=selected_wells,
            )
            annotations = create_map_annotations(
                formation=formation,
                surface_data=surf_data,
                colortables=self._color_tables,
                attribute=attribute,
            )
            viewports = no_update if current_views else create_map_viewports()
            return (layers, annotations, viewports)

        @callback(
            Output(ViewSettings.Ids.OPTIONS_DIALOG, "open"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_BUTTON, "n_clicks"),
        )
        def open_close_options_dialog(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate

        @callback(
            Output(ViewSettings.Ids.FEEDBACK, "open"),
            Input(ViewSettings.Ids.FEEDBACK_BUTTON, "n_clicks"),
        )
        def open_close_feedback(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate
