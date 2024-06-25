import logging
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
    process_containment_info,
    process_summed_mass,
    process_visualization_info,
    property_origin,
    readable_name,
    set_plot_ids,
)
from webviz_subsurface.plugins._co2_leakage._utilities.fault_polygons import (
    FaultPolygonsHandler,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    GraphSource,
    MapAttribute,
)
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import (
    init_map_attribute_names,
    init_menu_options,
    init_surface_providers,
    init_table_provider,
    init_well_pick_provider,
    process_files,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import (
    MainView,
    MapViewElement,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings

from . import _error
from ._utilities.color_tables import co2leakage_color_tables

LOGGER = logging.getLogger(__name__)
TABLES_PATH = "share/results/tables"


# pylint: disable=too-many-instance-attributes
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
        plume_mass_relpath: str = TABLES_PATH + "/plume_mass.csv",
        plume_actual_volume_relpath: str = TABLES_PATH + "/plume_actual_volume.csv",
        unsmry_relpath: Optional[str] = None,
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        initial_surface: Optional[str] = None,
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._error_message = ""
        try:
            ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }
            (
                containment_poly_dict,
                hazardous_poly_dict,
                well_pick_dict,
            ) = process_files(
                file_containment_boundary,
                file_hazardous_boundary,
                well_pick_file,
                ensemble_paths,
            )
            self._polygon_files = [containment_poly_dict, hazardous_poly_dict]
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
                    ensemble_paths[ens],
                    map_surface_names_to_fault_polygons or {},
                    fault_polygon_attribute,
                )
                for ens in ensembles
            }
            # CO2 containment
            self._co2_table_providers = init_table_provider(
                ensemble_paths,
                plume_mass_relpath,
            )
            self._co2_actual_volume_table_providers = init_table_provider(
                ensemble_paths,
                plume_actual_volume_relpath,
            )
            self._unsmry_providers = (
                init_table_provider(
                    ensemble_paths,
                    unsmry_relpath,
                )
                if unsmry_relpath is not None
                else None
            )
            # Well picks
            self._well_pick_provider = init_well_pick_provider(
                well_pick_dict,
                map_surface_names_to_well_pick_names,
            )
            # Phase (in case of residual trapping), zone and region options
            self._menu_options = init_menu_options(
                ensemble_paths,
                self._co2_table_providers,
                self._co2_actual_volume_table_providers,
                plume_mass_relpath,
                plume_actual_volume_relpath,
            )
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

        self._summed_co2: Dict[str, Any] = {}
        self._visualization_info = {
            "threshold": -1.0,
            "n_clicks": 0,
            "change": False,
            "unit": "kg",
        }
        self._color_tables = co2leakage_color_tables()
        self._well_pick_names = {
            ens: prov.well_names() if prov is not None else []
            for ens, prov in self._well_pick_provider.items()
        }
        self.add_shared_settings_group(
            ViewSettings(
                ensemble_paths,
                self._ensemble_surface_providers,
                initial_surface,
                self._map_attribute_names,
                [c["name"] for c in self._color_tables],  # type: ignore
                self._well_pick_names,
                self._menu_options,
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

    # Might want to do some refactoring if this gets too big
    # pylint: disable=too-many-statements
    def _set_callbacks(self) -> None:
        # Cannot avoid many arguments since all the parameters are needed
        # to determine what to plot
        # pylint: disable=too-many-arguments
        @callback(
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Output(
                self._view_component(MapViewElement.Ids.TIME_PLOT_ONE_REAL), "figure"
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
            Input(self._settings_component(ViewSettings.Ids.REGION), "value"),
            Input(self._settings_component(ViewSettings.Ids.PHASE), "value"),
            Input(self._settings_component(ViewSettings.Ids.CONTAINMENT), "value"),
            Input(self._settings_component(ViewSettings.Ids.COLOR_BY), "value"),
            Input(self._settings_component(ViewSettings.Ids.MARK_BY), "value"),
            Input(self._settings_component(ViewSettings.Ids.SORT_PLOT), "value"),
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
            region: Optional[str],
            phase: str,
            containment: str,
            color_choice: str,
            mark_choice: Optional[str],
            sorting: str,
        ) -> Tuple[Dict, go.Figure, go.Figure, go.Figure]:
            # pylint: disable=too-many-locals
            figs = [no_update] * 3
            cont_info = process_containment_info(
                zone,
                region,
                phase,
                containment,
                color_choice,
                mark_choice,
                sorting,
                self._menu_options[ensemble][source],
            )
            if source in [
                GraphSource.CONTAINMENT_MASS,
                GraphSource.CONTAINMENT_ACTUAL_VOLUME,
            ]:
                y_limits = [
                    y_min_val if len(y_min_auto) == 0 else None,
                    y_max_val if len(y_max_auto) == 0 else None,
                ]
                if (
                    source == GraphSource.CONTAINMENT_MASS
                    and ensemble in self._co2_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_table_providers[ensemble],
                        co2_scale,
                        realizations[0],
                        y_limits,
                        cont_info,
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
                        cont_info,
                    )
                set_plot_ids(figs, source, co2_scale, cont_info, realizations)
            elif source == GraphSource.UNSMRY:
                if self._unsmry_providers is not None:
                    if ensemble in self._unsmry_providers:
                        u_figs = generate_unsmry_figures(
                            self._unsmry_providers[ensemble],
                            co2_scale,
                            self._co2_table_providers[ensemble],
                        )
                        figs = list(u_figs)
                else:
                    LOGGER.warning(
                        """UNSMRY file has not been specified as input.
                         Please use unsmry_relpath in the configuration."""
                    )
            return figs  # type: ignore

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
            return dates, max(dates.keys())

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
        )
        def toggle_date_slider(attribute: str) -> Dict[str, str]:
            if MapAttribute(attribute) in [
                MapAttribute.MIGRATION_TIME_SGAS,
                MapAttribute.MIGRATION_TIME_AMFG,
            ]:
                return {"display": "none"}
            return {}

        @callback(
            Output(self._settings_component(ViewSettings.Ids.CO2_SCALE), "options"),
            Output(self._settings_component(ViewSettings.Ids.CO2_SCALE), "value"),
            Input(self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"),
        )
        def make_unit_list(
            attribute: str,
        ) -> Union[Tuple[List[Any], Co2MassScale], Tuple[List[Any], Co2VolumeScale],]:
            if attribute == GraphSource.CONTAINMENT_ACTUAL_VOLUME:
                return list(Co2VolumeScale), Co2VolumeScale.BILLION_CUBIC_METERS
            return list(Co2MassScale), Co2MassScale.MTONS

        @callback(
            Output(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "options"),
            Output(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "value"),
            Output(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "style"),
            Output(ViewSettings.Ids.WELL_FILTER_HEADER, "style"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def set_well_options(
            ensemble: str,
        ) -> Tuple[List[Any], List[str], Dict[Any, Any], Dict[Any, Any]]:
            return (
                [{"label": i, "value": i} for i in self._well_pick_names[ensemble]],
                self._well_pick_names[ensemble],
                {
                    "display": "block" if self._well_pick_names[ensemble] else "none",
                    "height": f"{len(self._well_pick_names[ensemble]) * 22}px",
                },
                {
                    "flex": 3,
                    "minWidth": "20px",
                    "display": "block" if self._well_pick_names[ensemble] else "none",
                },
            )

        # Cannot avoid many arguments and/or locals since all layers of the DeckGL map
        # need to be updated simultaneously
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
                self._settings_component(ViewSettings.Ids.VISUALIZATION_UPDATE),
                "n_clicks",
            ),
            Input(self._settings_component(ViewSettings.Ids.MASS_UNIT), "value"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_OPTIONS, "value"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "value"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
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
            visualization_update: int,
            mass_unit: str,
            options_dialog_options: List[int],
            selected_wells: List[str],
            ensemble: str,
            current_views: List[Any],
        ) -> Tuple[List[Dict[Any, Any]], List[Any], Dict[Any, Any]]:
            # Unable to clear cache (when needed) without the protected member
            # pylint: disable=protected-access
            self._visualization_info = process_visualization_info(
                visualization_update,
                visualization_threshold,
                mass_unit,
                self._visualization_info,
                self._surface_server._image_cache,
            )
            if self._visualization_info["change"]:
                return [], no_update, no_update
            attribute = MapAttribute(attribute)
            if len(realization) == 0 or ensemble is None:
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
            surf_data, summed_mass = None, None
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
                    visualization_info=self._visualization_info,
                    map_attribute_names=self._map_attribute_names,
                )
            assert isinstance(self._visualization_info["unit"], str)
            surf_data, self._summed_co2 = process_summed_mass(
                formation,
                realization,
                datestr,
                attribute,
                summed_mass,
                surf_data,
                self._summed_co2,
                self._visualization_info["unit"],
            )
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
                file_containment_boundary=self._polygon_files[0][ensemble],
                file_hazardous_boundary=self._polygon_files[1][ensemble],
                well_pick_provider=self._well_pick_provider[ensemble],
                plume_extent_data=plume_polygon,
                options_dialog_options=options_dialog_options,
                selected_wells=selected_wells,
            )
            annotations = create_map_annotations(
                formation=formation,
                surface_data=surf_data,
                colortables=self._color_tables,
                attribute=attribute,
                unit=self._visualization_info["unit"],
            )
            viewports = no_update if current_views else create_map_viewports()
            return layers, annotations, viewports

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

        @callback(
            Output(self._view_component(MapViewElement.Ids.TOP_ELEMENT), "style"),
            Output(self._view_component(MapViewElement.Ids.BOTTOM_ELEMENT), "style"),
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "style"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "style"),
            Output(
                self._view_component(MapViewElement.Ids.TIME_PLOT_ONE_REAL), "style"
            ),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
            Input(self._view_component(MapViewElement.Ids.SIZE_SLIDER), "value"),
            State(self._view_component(MapViewElement.Ids.TOP_ELEMENT), "style"),
            State(self._view_component(MapViewElement.Ids.BOTTOM_ELEMENT), "style"),
            Input(self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"),
        )
        def resize_plots(
            ensemble: str,
            slider_value: float,
            top_style: Dict,
            bottom_style: Dict,
            source: GraphSource,
        ) -> List[Dict]:
            bottom_style["height"] = f"{slider_value}vh"
            top_style["height"] = f"{80 - slider_value}vh"

            styles = [{"height": f"{slider_value * 0.9 - 4}vh", "width": "90%"}] * 3
            if source == GraphSource.UNSMRY and self._unsmry_providers is None:
                styles = [{"display": "none"}] * 3
            elif (
                source == GraphSource.CONTAINMENT_MASS
                and ensemble not in self._co2_table_providers
            ):
                styles = [{"display": "none"}] * 3
            elif (
                source == GraphSource.CONTAINMENT_ACTUAL_VOLUME
                and ensemble not in self._co2_actual_volume_table_providers
            ):
                styles = [{"display": "none"}] * 3

            return [top_style, bottom_style] + styles
