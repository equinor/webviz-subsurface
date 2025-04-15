import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import plotly.graph_objects as go
from dash import Dash, Input, Output, Patch, State, callback, ctx, html, no_update
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum, callback_typecheck

from webviz_subsurface._providers import FaultPolygonsServer, SurfaceImageServer
from webviz_subsurface._providers.ensemble_polygon_provider import PolygonServer
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import (
    SurfaceData,
    create_map_annotations,
    create_map_layers,
    create_map_viewports,
    derive_surface_address,
    extract_legendonly,
    generate_containment_figures,
    generate_unsmry_figures,
    get_plume_polygon,
    make_plot_ids,
    process_containment_info,
    process_summed_mass,
    process_visualization_info,
    property_origin,
    readable_name,
    set_plot_ids,
)
from webviz_subsurface.plugins._co2_leakage._utilities.fault_polygons_handler import (
    FaultPolygonsHandler,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    BoundarySettings,
    Co2MassScale,
    Co2VolumeScale,
    GraphSource,
    MapAttribute,
    MapThresholds,
    MapType,
)
from webviz_subsurface.plugins._co2_leakage._utilities.initialization import (
    init_containment_data_providers,
    init_dictionary_of_content,
    init_map_attribute_names,
    init_menu_options,
    init_polygon_provider_handlers,
    init_realizations,
    init_surface_providers,
    init_unsmry_data_providers,
    init_well_pick_provider,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.mainview import (
    MainView,
    MapViewElement,
)
from webviz_subsurface.plugins._co2_leakage.views.mainview.settings import ViewSettings

from . import _error
from ._types import LegendData
from ._utilities.color_tables import co2leakage_color_tables
from ._utilities.containment_info import StatisticsTabOption

LOGGER = logging.getLogger(__name__)
TABLES_PATH = "share/results/tables"


# pylint: disable=too-many-instance-attributes
class CO2Leakage(WebvizPluginABC):
    """Plugin for analyzing CO2 leakage potential across multiple realizations in an
    FMU ensemble

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`well_pick_file`:** Path to a file containing well picks
    * **`plume_mass_relpath`:** Path to a table of co2 _containment data_ for co2 mass
    * **`plume_actual_volume_relpath`:** Path to a table of co2 _containment data_ for co2
        volume of type "actual"
    * **`unsmry_relpath`:** Path to a csv/arrow version of a Cirrus/Eclipse unified summary
        file
    * **`fault_polygon_attribute`:** Polygons with this attribute are used as fault polygons
    * **`map_attribute_names`:** Key-value pairs for overriding the default mapping between
        attributes visualized by the plugin and attributes names used by
        EnsembleSurfaceProvider
    * **`initial_surface`:** Name of the surface/formation to show when the plugin is
        launched. If not provided, the first alphabetical surface is shown.
    * **`map_surface_names_to_well_pick_names`:** Mapping between surface map names and
        surface names used in the well pick file
    * **`map_surface_names_to_fault_polygons`:** Mapping between surface map names and
        surface names used by the fault polygons
    * **`boundary_settings`:** Settings for polygons representing the containment and
        hazardous areas
    ---

    This plugin is tightly linked to the FMU CCS post-process available in the ccs-scripts
    repository. If the ccs-scripts workflow is executed without alterations, there is no
    need for any configuration except the `ensembles` keyword. If any steps of the
    post-process are skipped, the plugin will exclude the respective results and
    functionality.

    Even though the workflow is standardized, it is sometimes necessary to override
    specific settings. For all path settings, these are interpreted relative to the
    realization root, but can also be absolute paths. Their default values are
    - `well_pick_file`: `share/results/well_picks.csv`
    - `plume_mass_relpath`: `share/results/tables/plume_mass.csv`
    - `plume_actual_volume_relpath`: No value
    - `unsmry_relpath`: No value

    Fault polygons are assumed to be stored in the `share/results/polygons` folder, and
    with a `dl_extracted_faultlines` attribute. This attribute can be overridden with
    `fault_polygon_attribute`, but the relative path to the polygons cannot.

    `map_attribute_names` can be used to override how attributes are mapped to specific
    features of the plugin. For instance, the attribute `migration_time_sgas` is mapped to
    the Migration Time (SGAS) visualization, but this can be overridden by specifying
    ```
    map_attribute_names:
      MIGRATION_TIME_SGAS: mig_time
    ```

    The following keys are allowed: `MIGRATION_TIME_SGAS, MIGRATION_TIME_AMFG,
    MIGRATION_TIME_XMF2, MAX_SGAS, MAX_AMFG, MAX_XMF2, MAX_SGSTRAND, MAX_SGTRH, MASS,
    DISSOLVED, FREE, FREE_GAS, TRAPPED_GAS`

    Well pick files and fault polygons might name surfaces differently than the ones
    generated by the ccs-scripts workflow. The options
    `map_surface_names_to_well_pick_names` and `map_surface_names_to_fault_polygons` can
    be used to specify this mapping explicitly. For instance, if the well pick file
    contains a surface called `top_sgas`, but the ccs-scripts workflow generated a
    surface called `top_sgas_2`, this can be specified with
    ```
    map_surface_names_to_well_pick_names:
      top_sgas_2: top_sgas
    ```
    Similar for `map_surface_names_to_fault_polygons`.

    `boundary_settings` is the final override option, and it can be used to specify
    polygons representing the containment and hazardous areas. By default, the polygons are
    expected to be named:
    - `share/results/polygons/containment--boundary.csv`
    - `share/results/polygons/hazarduous--boundary.csv`

    This corresponds to the following input:
    ```
    boundary_settings:
      polygon_file_pattern: share/results/polygons/*.csv
      attribute: boundary
      hazardous_name: hazardous
      containment_name: containment
    ```
    All four settings are optional, and if not specified, the default values are used.
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
        well_pick_file: Optional[str] = None,
        plume_mass_relpath: str = TABLES_PATH + "/plume_mass.csv",
        plume_actual_volume_relpath: Optional[str] = None,
        unsmry_relpath: Optional[str] = None,
        fault_polygon_attribute: str = "dl_extracted_faultlines",
        initial_surface: Optional[str] = None,
        map_attribute_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
        map_surface_names_to_fault_polygons: Optional[Dict[str, str]] = None,
        boundary_settings: Optional[BoundarySettings] = None,
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
            self._realizations_per_ensemble = init_realizations(ensemble_paths)
            self._surface_server = SurfaceImageServer.instance(app)
            self._polygons_server = FaultPolygonsServer.instance(app)
            self._map_attribute_names = init_map_attribute_names(
                webviz_settings, ensembles, map_attribute_names
            )
            self._map_thresholds = MapThresholds(self._map_attribute_names)
            self._threshold_ids = list(self._map_thresholds.standard_thresholds.keys())
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
            self._co2_table_providers = init_containment_data_providers(
                ensemble_paths,
                plume_mass_relpath,
            )
            self._co2_actual_volume_table_providers = init_containment_data_providers(
                ensemble_paths,
                plume_actual_volume_relpath,
            )
            self._unsmry_providers = init_unsmry_data_providers(
                ensemble_paths,
                unsmry_relpath,
            )
            self._polygon_handlers = init_polygon_provider_handlers(
                PolygonServer.instance(app),
                ensemble_paths,
                boundary_settings,
            )
            # Well picks
            self._well_pick_provider = init_well_pick_provider(
                ensemble_paths,
                well_pick_file,
                map_surface_names_to_well_pick_names,
            )
            # Phase (in case of residual trapping), zone and region options
            self._menu_options = init_menu_options(
                ensemble_paths,
                self._co2_table_providers,
                self._co2_actual_volume_table_providers,
                self._unsmry_providers,
            )
            self._content = init_dictionary_of_content(
                self._menu_options,
                len(self._map_attribute_names.mapping) > 0,
            )
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

        self._summed_co2: Dict[str, Any] = {}
        self._visualization_info = {
            "thresholds": self._map_thresholds.standard_thresholds,
            "n_clicks": 0,
            "change": False,
            "unit": "tons",
        }
        self._color_tables = co2leakage_color_tables()
        self._well_pick_names: Dict[str, List[str]] = {
            ens: (
                self._well_pick_provider[ens].well_names
                if ens in self._well_pick_provider
                else []
            )
            for ens in ensembles
        }
        self.add_shared_settings_group(
            ViewSettings(
                ensemble_paths,
                self._realizations_per_ensemble,
                self._ensemble_surface_providers,
                initial_surface,
                self._map_attribute_names,
                self._map_thresholds,
                [c["name"] for c in self._color_tables],  # type: ignore
                self._well_pick_names,
                self._menu_options,
                self._content,
            ),
            self.Ids.MAIN_SETTINGS,
        )
        self.add_view(MainView(self._color_tables, self._content), self.Ids.MAIN_VIEW)

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
        date_map_attribute = next(
            (
                k
                for k in self._map_attribute_names.filtered_values
                if MapType[k.name].value != "MIGRATION_TIME"
            ),
            None,
        )
        att_name = (
            self._map_attribute_names[date_map_attribute]
            if date_map_attribute is not None
            else None
        )
        dates = (
            None
            if att_name is None
            else surface_provider.surface_dates_for_attribute(att_name)
        )
        if dates is None:
            raise ValueError(f"Failed to fetch dates for attribute '{att_name}'")
        return dates

    # Might want to do some refactoring if this gets too big
    def _set_callbacks(self) -> None:
        if self._content["any_table"]:
            self._add_graph_callback()
            self._add_legend_change_callback()
            self._add_set_unit_list_callback()
            self._add_time_plot_visibility_callback()

        if self._content["maps"]:
            self._add_set_dates_callback()
            self._add_date_slider_visibility_callback()
            self._add_set_well_options_callback()
            self._add_create_map_callback()
            self._add_options_dialog_callback()
            self._add_thresholds_dialog_callback()

        self._add_feedback_dialog_callback()

        if self._content["maps"] and self._content["any_table"]:
            self._add_resize_plot_callback()

    def _add_resize_plot_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.TOP_ELEMENT), "style"),
            Output(self._view_component(MapViewElement.Ids.BOTTOM_ELEMENT), "style"),
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "style"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "style"),
            Output(self._view_component(MapViewElement.Ids.STATISTICS_PLOT), "style"),
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

    def _add_feedback_dialog_callback(self) -> None:
        @callback(
            Output(ViewSettings.Ids.FEEDBACK, "open"),
            Input(ViewSettings.Ids.FEEDBACK_BUTTON, "n_clicks"),
        )
        def open_close_feedback(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate

    def _add_thresholds_dialog_callback(self) -> None:
        @callback(
            Output(ViewSettings.Ids.VISUALIZATION_THRESHOLD_DIALOG, "open"),
            Input(ViewSettings.Ids.VISUALIZATION_THRESHOLD_BUTTON, "n_clicks"),
        )
        def open_close_thresholds(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate

    def _add_options_dialog_callback(self) -> None:
        @callback(
            Output(ViewSettings.Ids.OPTIONS_DIALOG, "open"),
            Input(ViewSettings.Ids.OPTIONS_DIALOG_BUTTON, "n_clicks"),
        )
        def open_close_options_dialog(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate

    def _add_create_map_callback(self) -> None:
        # Cannot avoid many arguments and/or locals since all layers of the DeckGL map
        # need to be updated simultaneously
        # pylint: disable=too-many-arguments,too-many-locals
        @callback(
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "layers"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "children"),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "views"),
            inputs={
                "attribute": Input(
                    self._settings_component(ViewSettings.Ids.PROPERTY), "value"
                ),
                "date": Input(
                    self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"
                ),
                "formation": Input(
                    self._settings_component(ViewSettings.Ids.FORMATION), "value"
                ),
                "realization": Input(
                    self._settings_component(ViewSettings.Ids.REALIZATION), "value"
                ),
                "statistic": Input(
                    self._settings_component(ViewSettings.Ids.STATISTIC), "value"
                ),
                "color_map_name": Input(
                    self._settings_component(ViewSettings.Ids.COLOR_SCALE), "value"
                ),
                "cm_min_auto": Input(
                    self._settings_component(ViewSettings.Ids.CM_MIN_AUTO), "value"
                ),
                "cm_min_val": Input(
                    self._settings_component(ViewSettings.Ids.CM_MIN), "value"
                ),
                "cm_max_auto": Input(
                    self._settings_component(ViewSettings.Ids.CM_MAX_AUTO), "value"
                ),
                "cm_max_val": Input(
                    self._settings_component(ViewSettings.Ids.CM_MAX), "value"
                ),
                "plume_threshold": Input(
                    self._settings_component(ViewSettings.Ids.PLUME_THRESHOLD),
                    "value",
                ),
                "plume_smoothing": Input(
                    self._settings_component(ViewSettings.Ids.PLUME_SMOOTHING),
                    "value",
                ),
                "visualization_update": Input(
                    self._settings_component(ViewSettings.Ids.VISUALIZATION_UPDATE),
                    "n_clicks",
                ),
                "mass_unit": Input(
                    self._settings_component(ViewSettings.Ids.MASS_UNIT), "value"
                ),
                "mass_unit_update": Input(
                    self._settings_component(ViewSettings.Ids.MASS_UNIT_UPDATE),
                    "n_clicks",
                ),
                "options_dialog_options": Input(
                    ViewSettings.Ids.OPTIONS_DIALOG_OPTIONS, "value"
                ),
                "selected_wells": Input(
                    ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER, "value"
                ),
                "ensemble": Input(
                    self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"
                ),
                "current_views": State(
                    self._view_component(MapViewElement.Ids.DECKGL_MAP), "views"
                ),
                "thresholds": [Input(id, "value") for id in self._threshold_ids],
            },
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
            visualization_update: int,
            mass_unit: str,
            mass_unit_update: int,
            options_dialog_options: List[int],
            selected_wells: List[str],
            ensemble: str,
            current_views: List[Any],
            thresholds: List[float],
        ) -> Tuple[List[Dict[Any, Any]], Optional[List[Any]], Dict[Any, Any]]:
            # Unable to clear cache (when needed) without the protected member
            # pylint: disable=protected-access
            current_thresholds = dict(zip(self._threshold_ids, thresholds))
            assert visualization_update >= 0  # Need the input to trigger callback
            assert mass_unit_update >= 0  # These are just to silence pylint
            self._visualization_info = process_visualization_info(
                attribute,
                current_thresholds,
                mass_unit,
                self._visualization_info,
                self._surface_server._image_cache,
            )
            if self._visualization_info["change"]:
                return [], None, no_update
            attribute = MapAttribute(attribute)
            if len(realization) == 0 or ensemble is None:
                raise PreventUpdate
            if isinstance(date, int):
                datestr = self._ensemble_dates(ensemble)[date]
            elif date is None:
                datestr = None
            # Contour data
            contour_data = None
            if MapType[MapAttribute(attribute).name].value == "PLUME":
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
            fault_polygon_url = self._fault_polygon_handlers[
                ensemble
            ].extract_fault_polygon_url(formation, realization)
            hazardous_polygon_url = self._polygon_handlers[
                ensemble
            ].extract_hazardous_poly_url(realization)
            containment_polygon_url = self._polygon_handlers[
                ensemble
            ].extract_containment_poly_url(realization)
            layers = create_map_layers(
                realizations=realization,
                formation=formation,
                surface_data=surf_data,
                fault_polygon_url=fault_polygon_url,
                containment_bounds_url=containment_polygon_url,
                haz_bounds_url=hazardous_polygon_url,
                well_pick_provider=self._well_pick_provider.get(ensemble, None),
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

    def _add_set_well_options_callback(self) -> None:
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
                    "display": ("block" if self._well_pick_names[ensemble] else "none"),
                    "height": f"{len(self._well_pick_names[ensemble]) * 22}px",
                },
                {
                    "flex": 3,
                    "minWidth": "20px",
                    "display": ("block" if self._well_pick_names[ensemble] else "none"),
                },
            )

    def _add_date_slider_visibility_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"),
            Input(self._settings_component(ViewSettings.Ids.PROPERTY), "value"),
        )
        def toggle_date_slider(attribute: str) -> Dict[str, str]:
            if MapType[MapAttribute(attribute).name].value == "MIGRATION_TIME":
                return {"display": "none"}
            return {}

    def _add_set_dates_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), "marks"),
            Output(self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"),
            Input(self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"),
        )
        def set_dates(
            ensemble: str,
        ) -> Tuple[Dict[int, Dict[str, Any]], Optional[int]]:
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
            if len(dates.keys()) > 0:
                return dates, max(dates.keys())
            return dates, None

    def _add_time_plot_visibility_callback(self) -> None:
        @callback(
            Output(self._settings_component(ViewSettings.Ids.REAL_OR_STAT), "style"),
            Output(self._settings_component(ViewSettings.Ids.Y_LIM_OPTIONS), "style"),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
        )
        def toggle_time_plot_options_visibility(
            realizations: List[int],
        ) -> Tuple[Dict[str, str], Dict[str, str]]:
            if len(realizations) == 1:
                return (
                    {"display": "none"},
                    {"display": "flex", "flex-direction": "column"},
                )
            return (
                {"display": "flex", "flex-direction": "row"},
                {"display": "none"},
            )

    def _add_set_unit_list_callback(self) -> None:
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

    def _add_graph_callback(self) -> None:
        # Cannot avoid many arguments since all the parameters are needed
        # to determine what to plot
        # pylint: disable=too-many-arguments
        @callback(
            Output(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Output(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Output(
                self._view_component(MapViewElement.Ids.STATISTICS_PLOT),
                "figure",
            ),
            # LEGEND_DATA_STORE is updated whenever the legend is clicked. However,
            # there is not need to update the plots based on this change, since that
            # is done by plotly internally. We therefore use State instead of Input
            State(self._view_component(MapViewElement.Ids.LEGEND_DATA_STORE), "data"),
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
            Input(self._settings_component(ViewSettings.Ids.PLUME_GROUP), "value"),
            Input(self._settings_component(ViewSettings.Ids.COLOR_BY), "value"),
            Input(self._settings_component(ViewSettings.Ids.MARK_BY), "value"),
            Input(self._settings_component(ViewSettings.Ids.SORT_PLOT), "value"),
            Input(self._settings_component(ViewSettings.Ids.REAL_OR_STAT), "value"),
            Input(self._settings_component(ViewSettings.Ids.DATE_OPTION), "value"),
            Input(
                self._settings_component(ViewSettings.Ids.STATISTICS_TAB_OPTION),
                "value",
            ),
            Input(self._settings_component(ViewSettings.Ids.BOX_SHOW_POINTS), "value"),
        )
        @callback_typecheck
        def update_graphs(
            legend_data: LegendData,
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
            plume_group: str,
            color_choice: str,
            mark_choice: Optional[str],
            sorting: str,
            lines_to_show: str,
            date_option: str,
            statistics_tab_option: StatisticsTabOption,
            box_show_points: str,
        ) -> Tuple[Dict, go.Figure, go.Figure, go.Figure]:
            # pylint: disable=too-many-locals
            figs = [no_update] * 3
            cont_info = process_containment_info(
                zone,
                region,
                phase,
                containment,
                plume_group,
                color_choice,
                mark_choice,
                sorting,
                lines_to_show,
                date_option,
                statistics_tab_option,
                box_show_points,
                self._menu_options[ensemble][source],
            )
            if source in [
                GraphSource.CONTAINMENT_MASS,
                GraphSource.CONTAINMENT_ACTUAL_VOLUME,
            ]:
                plot_ids = make_plot_ids(
                    ensemble,
                    source,
                    co2_scale,
                    cont_info,
                    realizations,
                    len(figs),
                )
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
                        realizations,
                        y_limits,
                        cont_info,
                        legend_data,
                    )
                elif (
                    source == GraphSource.CONTAINMENT_ACTUAL_VOLUME
                    and ensemble in self._co2_actual_volume_table_providers
                ):
                    figs[: len(figs)] = generate_containment_figures(
                        self._co2_actual_volume_table_providers[ensemble],
                        co2_scale,
                        realizations,
                        y_limits,
                        cont_info,
                        legend_data,
                    )
                set_plot_ids(figs, plot_ids)
            elif source == GraphSource.UNSMRY:
                if self._unsmry_providers is not None:
                    if ensemble in self._unsmry_providers:
                        figs[0] = go.Figure()
                        figs[1] = generate_unsmry_figures(
                            self._unsmry_providers[ensemble],
                            co2_scale,
                            self._co2_table_providers[ensemble],
                        )
                        figs[2] = go.Figure()
                else:
                    LOGGER.warning(
                        """UNSMRY file has not been specified as input.
                         Please use unsmry_relpath in the configuration."""
                    )
            return figs  # type: ignore

    def _add_legend_change_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.LEGEND_DATA_STORE), "data"),
            Input(self._view_component(MapViewElement.Ids.BAR_PLOT), "restyleData"),
            State(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Input(self._view_component(MapViewElement.Ids.TIME_PLOT), "restyleData"),
            State(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Input(
                self._view_component(MapViewElement.Ids.STATISTICS_PLOT), "restyleData"
            ),
            State(self._view_component(MapViewElement.Ids.STATISTICS_PLOT), "figure"),
            Input(
                self._settings_component(ViewSettings.Ids.STATISTICS_TAB_OPTION),
                "value",
            ),
        )
        def on_bar_legend_update(
            bar_event: List[Any],
            bar_figure: go.Figure,
            time_event: List[Any],
            time_figure: go.Figure,
            stats_event: List[Any],
            stats_figure: go.Figure,
            _: StatisticsTabOption,
        ) -> Patch:
            # We cannot subscribe to a legend click event directly, but we can subscribe
            # to the more general "restyleData" event, and then try to identify if this
            # was a click event or not. If yes, we update the appropriate store component
            p = Patch()
            _id = ctx.triggered_id
            if _id is None:
                return p

            if _id == self._view_component(MapViewElement.Ids.BAR_PLOT):
                if self._is_legend_click_event(bar_event):
                    p["bar_legendonly"] = extract_legendonly(bar_figure)
            elif _id == self._view_component(MapViewElement.Ids.TIME_PLOT):
                if self._is_legend_click_event(time_event):
                    p["time_legendonly"] = extract_legendonly(time_figure)
            elif _id in (
                self._view_component(MapViewElement.Ids.STATISTICS_PLOT),
                self._settings_component(ViewSettings.Ids.STATISTICS_TAB_OPTION),
            ):
                if self._is_legend_click_event(stats_event):
                    p["stats_legendonly"] = extract_legendonly(stats_figure)
            return p

    @staticmethod
    def _is_legend_click_event(event: List[Any]) -> bool:
        # A typical legend click event would be: [{'visible': ['legendonly']}, [1]]
        if event is None or not isinstance(event, list):
            return False
        return any("visible" in e for e in event if isinstance(e, dict))
