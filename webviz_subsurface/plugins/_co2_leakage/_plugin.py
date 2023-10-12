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
)
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import (
    init_map_attribute_names,
    init_surface_providers,
    init_table_provider,
    init_well_pick_provider,
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
    * **`co2_containment_relpath`:** Path to a table of co2 containment data (amount of
        CO2 outside/inside a boundary), for co2 mass. Relative to each realization.
    * **`co2_containment_volume_actual_relpath`:** Path to a table of co2 containment data (amount
        of CO2 outside/inside a boundary), for co2 volume of type "actual". Relative to each
        realization.
    * **`co2_containment_volume_actual_simple_relpath`:** Path to a table of co2 containment data
        (amount of CO2 outside/inside a boundary), for co2 volume of type "actual_simple".
        Relative to each realization.
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
        co2_containment_relpath: str = TILE_PATH + "/co2_volumes.csv",
        co2_containment_volume_actual_relpath: str = TILE_PATH
        + "/plume_volume_actual.csv",
        co2_containment_volume_actual_simple_relpath: str = TILE_PATH
        + "/plume_volume_actual_simple.csv",
        unsmry_relpath: str = TILE_PATH + "/unsmry--raw.csv",
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        initial_surface: Optional[str] = None,
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._error_message = ""

        self._file_containment_boundary = file_containment_boundary
        self._file_hazardous_boundary = file_hazardous_boundary
        try:
            self._ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }
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
                co2_containment_relpath,
            )
            self._co2_volume_actual_table_providers = init_table_provider(
                self._ensemble_paths,
                co2_containment_volume_actual_relpath,
            )
            self._co2_volume_actual_simple_table_providers = init_table_provider(
                self._ensemble_paths,
                co2_containment_volume_actual_simple_relpath,
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
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

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
        ) -> Tuple[go.Figure, go.Figure, Dict, Dict]:
            styles = [{"display": "none"}] * 3
            figs = [no_update] * 3
            if source in [
                GraphSource.CONTAINMENT_MASS,
                GraphSource.CONTAINMENT_VOLUME_ACTUAL,
                GraphSource.CONTAINMENT_VOLUME_ACTUAL_SIMPLE,
            ]:
                y_limits = []
                if len(y_min_auto) == 0:
                    y_limits.append(y_min_val)
                else:
                    y_limits.append(None)
                if len(y_max_auto) == 0:
                    y_limits.append(y_max_val)
                else:
                    y_limits.append(None)
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
                    )
                elif (
                    source == GraphSource.CONTAINMENT_VOLUME_ACTUAL
                    and ensemble in self._co2_volume_actual_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_volume_actual_table_providers[ensemble],
                        co2_scale,
                        realizations[0],
                        y_limits,
                    )
                elif (
                    source == GraphSource.CONTAINMENT_VOLUME_ACTUAL_SIMPLE
                    and ensemble in self._co2_volume_actual_simple_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_volume_actual_simple_table_providers[ensemble],
                        co2_scale,
                        realizations[0],
                        y_limits,
                    )
            elif source == GraphSource.UNSMRY and ensemble in self._unsmry_providers:
                u_figs = generate_unsmry_figures(
                    self._unsmry_providers[ensemble],
                    co2_scale,
                    self._co2_table_providers[ensemble],
                )
                figs[: len(u_figs)] = u_figs
                styles[: len(u_figs)] = [{}] * len(u_figs)

            return *figs, *styles  # type: ignore

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
            if attribute in [
                GraphSource.CONTAINMENT_VOLUME_ACTUAL,
                GraphSource.CONTAINMENT_VOLUME_ACTUAL_SIMPLE,
            ]:
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
            Input(ViewSettings.Ids.OPTIONS_DIALOG_OPTIONS, "value"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "value"),
            State(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
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
            options_dialog_options: List[int],
            selected_wells: List[str],
            ensemble: str,
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
            )
            viewports = create_map_viewports()
            return (layers, annotations, viewports)

        @callback(
            Output(ViewSettings.Ids.OPTIONS_DIALOG, "open"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_BUTTON, "n_clicks"),
        )
        def open_close_options_dialog(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate
