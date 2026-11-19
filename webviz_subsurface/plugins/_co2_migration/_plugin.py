# pylint: disable=too-many-lines
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import plotly.graph_objects as go
from dash import Dash, Input, Output, Patch, State, callback, ctx, html, no_update
from dash._callback import NoUpdate
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum, callback_typecheck

from webviz_subsurface._providers import FaultPolygonsServer, SurfaceImageServer
from webviz_subsurface._providers.ensemble_polygon_provider import PolygonServer
from webviz_subsurface.plugins._co2_migration._utilities.callbacks import (
    SurfaceData,
    create_map_annotations,
    create_map_layers,
    derive_surface_address,
    export_figure_data_to_csv,
    extract_legendonly,
    find_table_date,
    generate_containment_figure,
    generate_unsmry_figures,
    make_plot_generation_key,
    make_plot_id,
    process_containment_info,
    process_summed_mass,
    property_origin,
    readable_name,
)
from webviz_subsurface.plugins._co2_migration._utilities.fault_polygons_handler import (
    FaultPolygonsHandler,
)
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    BoundarySettings,
    Co2MassScale,
    Co2VolumeScale,
    GraphSource,
    MapAttribute,
    MapThresholds,
    MapType,
    check_hazardous_polygon,
    deactivate_polygon_warnings,
)
from webviz_subsurface.plugins._co2_migration._utilities.initialization import (
    init_containment_data_providers,
    init_dates_per_ensemble,
    init_dictionary_of_content,
    init_map_attribute_names,
    init_menu_options,
    init_polygon_provider_handlers,
    init_realizations,
    init_surface_providers,
    init_unsmry_data_providers,
    init_well_pick_provider,
)
from webviz_subsurface.plugins._co2_migration.views.mainview.mainview import (
    DATE_SLIDER_HEIGHT,
    DATE_SLIDER_STYLE,
    MainView,
    MapViewElement,
)
from webviz_subsurface.plugins._co2_migration.views.mainview.settings import (
    HIDDEN,
    ROWS,
    SECTION,
    ViewSettings,
)

from . import _error
from ._types import LegendData
from ._utilities.color_tables import co2migration_color_tables
from ._utilities.containment_info import MainTabOption
from ._utilities.surface_publishing import SurfaceTransform

LOGGER = logging.getLogger(__name__)
TABLES_PATH = "share/results/tables"


# pylint: disable=too-many-instance-attributes
class CO2Migration(WebvizPluginABC):
    """Plugin for analyzing CO2 migration across multiple realizations in an
    FMU ensemble

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`well_pick_file`:** Path to a file containing well picks. A relative path is
        read from each realization; an absolute path is one file used for all
        realizations. If the file is missing or cannot be read, no well picks are shown.
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
        nogo areas
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
    MIGRATION_TIME_XMF2, MIGRATION_TIME_MASS, MAX_SGAS, MAX_AMFG, MAX_XMF2,
    MAX_SGSTRAND, MAX_SGTRH, MASS, DISSOLVED_WATER, DISSOLVED_OIL, FREE,
    FREE_GAS, TRAPPED_GAS`

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
    polygons representing the containment and nogo areas. By default, the polygons are
    expected to be named:
    - `share/results/polygons/containment--boundary.csv`
    - `share/results/polygons/nogo--boundary.csv`

    This corresponds to the following input:
    ```
    boundary_settings:
      polygon_file_pattern: share/results/polygons/*.csv
      attribute: boundary
      nogo_name: nogo
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
            deactivate_polygon_warnings()
            check_hazardous_polygon(boundary_settings)
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
            # Dates, shared by maps and graphs through the date slider
            self._ensemble_dates = init_dates_per_ensemble(
                ensembles,
                self._map_attribute_names,
                self._ensemble_surface_providers,
                self._menu_options,
            )
            self._content = init_dictionary_of_content(
                self._menu_options,
                len(self._map_attribute_names.mapping) > 0,
            )
        except Exception as err:
            self._error_message = f"Plugin initialization failed: {err}"
            raise

        self._summed_co2: Dict[str, Any] = {}
        self._color_tables = co2migration_color_tables()
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
    def layout(self) -> html.Div:  # type: ignore[override]
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

    # Might want to do some refactoring if this gets too big
    def _set_callbacks(self) -> None:
        if self._content["any_table"]:
            self._add_graph_callback()
            self._add_legend_change_callback()
            self._add_set_unit_list_callback()
            self._add_time_plot_visibility_callback()
            self._add_csv_export_callback()
            self._add_resize_plot_callback()

        if self._content["maps"]:
            self._add_set_well_options_callback()
            self._add_create_map_callback()
            self._add_overlay_dialog_callback()
            self._add_thresholds_dialog_callback()

        self._add_set_dates_callback()
        self._add_date_slider_visibility_callback()
        self._add_feedback_dialog_callback()

    def _add_resize_plot_callback(self) -> None:
        has_maps = self._content["maps"]
        outputs = [
            Output(self._view_component(plot_id), "style")
            for plot_id in (
                MapViewElement.Ids.BAR_PLOT,
                MapViewElement.Ids.TIME_PLOT,
                MapViewElement.Ids.PROBABILITY_PLOT,
                MapViewElement.Ids.BOX_PLOT,
            )
        ]
        inputs = {
            "ensemble": Input(
                self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"
            ),
            "source": Input(
                self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"
            ),
            "date_slider_style": Input(
                self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"
            ),
        }
        if has_maps:
            outputs += [
                Output(self._view_component(MapViewElement.Ids.TOP_ELEMENT), "style"),
                Output(
                    self._view_component(MapViewElement.Ids.BOTTOM_ELEMENT), "style"
                ),
            ]
            inputs["slider_value"] = Input(
                self._view_component(MapViewElement.Ids.SIZE_SLIDER), "value"
            )

        @callback(output=outputs, inputs=inputs)
        def resize_plots(
            ensemble: str,
            source: GraphSource,
            date_slider_style: Dict[str, Any],
            slider_value: float = 0,
        ) -> List[Dict]:
            date_px = 0 if date_slider_style == HIDDEN else DATE_SLIDER_HEIGHT
            graph_height = (
                f"{slider_value * 0.9 - 4}vh"
                if has_maps
                else f"calc(90vh - {150 + date_px}px)"
            )
            styles = [{"height": graph_height, "width": "100%"}] * 4
            if source == GraphSource.UNSMRY and self._unsmry_providers is None:
                styles = [HIDDEN] * 4
            elif (
                source == GraphSource.CONTAINMENT_MASS
                and ensemble not in self._co2_table_providers
            ):
                styles = [HIDDEN] * 4
            elif (
                source == GraphSource.CONTAINMENT_ACTUAL_VOLUME
                and ensemble not in self._co2_actual_volume_table_providers
            ):
                styles = [HIDDEN] * 4

            if has_maps:
                # The date slider takes its height from the map frame
                styles += [
                    {"height": f"calc({80 - slider_value}vh - {date_px}px)"},
                    {"height": f"{slider_value}vh"},
                ]
            return styles

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

    def _add_overlay_dialog_callback(self) -> None:
        @callback(
            Output(ViewSettings.Ids.OVERLAY_DIALOG, "open"),
            Input(ViewSettings.Ids.OVERLAY_DIALOG_BUTTON, "n_clicks"),
        )
        def open_close_overlay_dialog(_n_clicks: Optional[int]) -> bool:
            if _n_clicks is not None:
                return _n_clicks > 0
            raise PreventUpdate

    def _add_create_map_callback(self) -> None:
        # Cannot avoid many arguments and/or locals since all layers of the DeckGL map
        # need to be updated simultaneously
        # pylint: disable=too-many-arguments,too-many-locals
        @callback(
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "layers"),
            Output(
                self._view_component(MapViewElement.Ids.MAP_ANNOTATIONS), "children"
            ),
            Output(self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"),
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
                "contour_switch": Input(
                    self._settings_component(ViewSettings.Ids.CONTOURS_SWITCH), "value"
                ),
                "contour_quantity": Input(
                    self._settings_component(ViewSettings.Ids.CONTOURS_QUANTITY),
                    "value",
                ),
                "plume_threshold": Input(
                    self._settings_component(ViewSettings.Ids.PLUME_THRESHOLD),
                    "value",
                ),
                "plume_smoothing": Input(
                    self._settings_component(ViewSettings.Ids.PLUME_SMOOTHING),
                    "value",
                ),
                "mass_unit": Input(
                    self._settings_component(ViewSettings.Ids.MASS_UNIT), "value"
                ),
                "overlay_dialog_options": Input(
                    ViewSettings.Ids.OVERLAY_DIALOG_OPTIONS, "value"
                ),
                "selected_wells": Input(
                    ViewSettings.Ids.OVERLAY_DIALOG_WELL_FILTER, "value"
                ),
                "ensemble": Input(
                    self._settings_component(ViewSettings.Ids.ENSEMBLE), "value"
                ),
                "thresholds": [Input(id, "value") for id in self._threshold_ids],
                "current_bounds": State(
                    self._view_component(MapViewElement.Ids.DECKGL_MAP), "bounds"
                ),
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
            contour_switch: List[str],
            contour_quantity: Optional[float],
            plume_threshold: Optional[float],
            plume_smoothing: Optional[float],
            mass_unit: str,
            overlay_dialog_options: List[str],
            selected_wells: List[str],
            ensemble: str,
            thresholds: List[Optional[float]],
            current_bounds: Optional[List[float]],
        ) -> Tuple[
            List[Dict[Any, Any]], Optional[List[Any]], Union[List[float], NoUpdate]
        ]:
            current_thresholds = dict(zip(self._threshold_ids, thresholds))
            attribute = MapAttribute(attribute)
            map_type = MapType[attribute.name].value
            visualization_threshold = (
                current_thresholds.get(attribute.value)
                if map_type not in ("PLUME", "MIGRATION_TIME")
                else None
            )
            if (
                map_type not in ("PLUME", "MIGRATION_TIME")
                and visualization_threshold is None
            ):
                raise PreventUpdate
            if len(realization) == 0 or ensemble is None:
                raise PreventUpdate
            if map_type == "MIGRATION_TIME":
                datestr = None
            else:
                datestr = self._ensemble_dates[ensemble][date]
            # Plume data
            plume_data = None
            if map_type == "PLUME":
                plume_data = {
                    "threshold": plume_threshold,
                    "smoothing": plume_smoothing,
                }
            # Surface
            surf_data, summed_mass = None, None
            if formation is not None and len(realization) > 0:
                surface_address = derive_surface_address(
                    formation,
                    attribute,
                    datestr,
                    realization,
                    self._map_attribute_names,
                    statistic,
                    plume_data,
                )
                surf_data, summed_mass = SurfaceData.from_server(
                    server=self._surface_server,
                    provider=self._ensemble_surface_providers[ensemble],
                    address=surface_address,
                    color_map_range=(
                        cm_min_val if len(cm_min_auto) == 0 else None,
                        cm_max_val if len(cm_max_auto) == 0 else None,
                    ),
                    color_map_name=color_map_name,
                    readable_name_=readable_name(attribute),
                    transform=SurfaceTransform(
                        map_attribute=attribute,
                        mass_unit=mass_unit,
                        visualization_threshold=visualization_threshold,
                    ),
                )
            current_summed_mass, self._summed_co2 = process_summed_mass(
                formation,
                realization,
                datestr,
                attribute,
                summed_mass,
                self._summed_co2,
                mass_unit,
            )
            # Create layers and view bounds
            fault_polygon_url = self._fault_polygon_handlers[
                ensemble
            ].extract_fault_polygon_url(formation, realization)
            nogo_polygon_url = self._polygon_handlers[ensemble].extract_nogo_poly_url(
                realization
            )
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
                nogo_bounds_url=nogo_polygon_url,
                hazardous_bounds_url=hazardous_polygon_url,
                well_pick_provider=self._well_pick_provider.get(ensemble, None),
                overlay_dialog_options=overlay_dialog_options,
                selected_wells=selected_wells,
                show_contours=len(contour_switch) > 0,
                num_contours=contour_quantity,
            )
            annotations = create_map_annotations(
                formation=formation,
                surface_data=surf_data,
                colortables=self._color_tables,
                attribute=attribute,
                unit=mass_unit,
                current_total=current_summed_mass,
                options=overlay_dialog_options,
                con_url=containment_polygon_url,
                haz_url=hazardous_polygon_url,
                nogo_url=nogo_polygon_url,
            )
            # The image layer reports pre-rotation bounds, so frame the true extent
            bounds: Union[List[float], NoUpdate] = no_update
            if surf_data is not None and not current_bounds:
                meta = surf_data.meta_data
                bounds = [meta.x_min, meta.y_min, meta.x_max, meta.y_max]
            return layers, annotations, bounds

    def _add_set_well_options_callback(self) -> None:
        @callback(
            Output(ViewSettings.Ids.OVERLAY_DIALOG_WELL_FILTER, "options"),
            Output(ViewSettings.Ids.OVERLAY_DIALOG_WELL_FILTER, "value"),
            Output(ViewSettings.Ids.OVERLAY_DIALOG_WELL_FILTER, "style"),
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
        inputs = {}
        if self._content["maps"]:
            inputs["attribute"] = Input(
                self._settings_component(ViewSettings.Ids.PROPERTY), "value"
            )
        if self._content["any_table"]:
            inputs["active_tab"] = Input(
                self._view_component(MapViewElement.Ids.SUMMARY_TABS), "value"
            )
            inputs["source"] = Input(
                self._settings_component(ViewSettings.Ids.GRAPH_SOURCE), "value"
            )

        @callback(
            Output(self._view_component(MapViewElement.Ids.DATE_WRAPPER), "style"),
            inputs=inputs,
        )
        def toggle_date_slider(
            attribute: Optional[str] = None,
            active_tab: Optional[str] = None,
            source: Optional[str] = None,
        ) -> Dict[str, Any]:
            map_uses_date = (
                attribute is not None
                and MapType[MapAttribute(attribute).name].value != "MIGRATION_TIME"
            )
            graph_uses_date = (
                active_tab is not None
                and active_tab != MainTabOption.CONTAINMENT_OVER_TIME
                and source != GraphSource.UNSMRY
            )
            return DATE_SLIDER_STYLE if map_uses_date or graph_uses_date else HIDDEN

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
            dates = {
                i: {
                    "label": f"{d[:4]}",
                    "style": {"writingMode": "vertical-rl"},
                }
                for i, d in enumerate(self._ensemble_dates[ensemble])
            }
            if len(dates.keys()) > 0:
                return dates, max(dates.keys())
            return dates, None

    def _add_time_plot_visibility_callback(self) -> None:
        @callback(
            Output(
                self._view_component(MapViewElement.Ids.TIME_PLOT_LINES_WRAPPER),
                "style",
            ),
            Output(self._settings_component(ViewSettings.Ids.Y_LIM_OPTIONS), "style"),
            Output(
                self._settings_component(ViewSettings.Ids.GRAPH_DISPLAY_HEADER),
                "style",
            ),
            Input(self._settings_component(ViewSettings.Ids.REALIZATION), "value"),
            Input(self._view_component(MapViewElement.Ids.SUMMARY_TABS), "value"),
        )
        def toggle_time_plot_options_visibility(
            realizations: List[int],
            active_tab: MainTabOption,
        ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
            single_real = len(realizations) == 1
            show_y_lim = (
                single_real and active_tab == MainTabOption.CONTAINMENT_OVER_TIME
            )
            return (
                HIDDEN if single_real else {},
                ROWS if show_y_lim else HIDDEN,
                SECTION if show_y_lim else HIDDEN,
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
                self._view_component(MapViewElement.Ids.PROBABILITY_PLOT),
                "figure",
            ),
            Output(self._view_component(MapViewElement.Ids.BOX_PLOT), "figure"),
            Output(
                self._view_component(MapViewElement.Ids.PLOT_GENERATION_STORE),
                "data",
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
            Input(self._view_component(MapViewElement.Ids.TIME_PLOT_LINES), "value"),
            Input(self._view_component(MapViewElement.Ids.DATE_SLIDER), "value"),
            Input(self._view_component(MapViewElement.Ids.OUTLIER_TOGGLE), "value"),
            Input(self._view_component(MapViewElement.Ids.SUMMARY_TABS), "value"),
            State(
                self._view_component(MapViewElement.Ids.PLOT_GENERATION_STORE),
                "data",
            ),
        )
        @callback_typecheck
        # pylint: disable=too-many-locals
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
            show_realizations: bool,
            date_index: Optional[int],
            show_all_points: bool,
            active_tab: MainTabOption,
            generation_keys: Optional[Dict[str, Any]],
        ) -> Tuple[Any, Any, Any, Any, Dict[str, Any]]:
            active_tab = MainTabOption(active_tab)
            active_index = {
                MainTabOption.CONTAINMENT_STATE: 0,
                MainTabOption.CONTAINMENT_OVER_TIME: 1,
                MainTabOption.PROBABILITY: 2,
                MainTabOption.BOX_PLOT: 3,
            }[active_tab]
            y_limits = [
                y_min_val if len(y_min_auto) == 0 else None,
                y_max_val if len(y_max_auto) == 0 else None,
            ]
            is_containment_source = source in (
                GraphSource.CONTAINMENT_MASS,
                GraphSource.CONTAINMENT_ACTUAL_VOLUME,
            )
            cont_info = None
            date_option = None
            if realizations and is_containment_source:
                menu_options = self._menu_options[ensemble][source]
                date_option = find_table_date(
                    self._ensemble_dates[ensemble], date_index, menu_options["dates"]
                )
                cont_info = process_containment_info(
                    zone,
                    region,
                    phase,
                    containment,
                    plume_group,
                    color_choice,
                    mark_choice,
                    sorting,
                    show_realizations,
                    date_option or "",
                    show_all_points,
                    menu_options,
                )

            generation_key = make_plot_generation_key(
                active_tab,
                ensemble,
                source,
                co2_scale,
                realizations,
                y_limits,
                cont_info,
            )
            updated_generation_keys = dict(generation_keys or {})
            if updated_generation_keys.get(active_tab.value) == generation_key:
                raise PreventUpdate

            figure = go.Figure()
            if realizations and is_containment_source:
                assert cont_info is not None
                table_provider = (
                    self._co2_table_providers.get(ensemble)
                    if source == GraphSource.CONTAINMENT_MASS
                    else self._co2_actual_volume_table_providers.get(ensemble)
                )
                # Dated plots are left empty if the slider date is missing in the table
                if table_provider is not None and (
                    date_option is not None
                    or active_tab == MainTabOption.CONTAINMENT_OVER_TIME
                ):
                    figure = generate_containment_figure(
                        table_provider,
                        active_tab,
                        co2_scale,
                        realizations,
                        y_limits,
                        cont_info,
                        legend_data,
                    )
                figure.layout.uirevision = make_plot_id(
                    ensemble,
                    source,
                    co2_scale,
                    cont_info,
                    realizations,
                    active_tab,
                )
            elif (
                realizations
                and source == GraphSource.UNSMRY
                and active_tab == MainTabOption.CONTAINMENT_OVER_TIME
            ):
                if (
                    self._unsmry_providers is not None
                    and ensemble in self._unsmry_providers
                    and ensemble in self._co2_table_providers
                ):
                    figure = generate_unsmry_figures(
                        self._unsmry_providers[ensemble],
                        co2_scale,
                        self._co2_table_providers[ensemble],
                    )
                else:
                    LOGGER.warning(
                        "UNSMRY data has not been specified for ensemble %s", ensemble
                    )
            figures = [no_update, no_update, no_update, no_update]
            figures[active_index] = figure
            updated_generation_keys[active_tab.value] = generation_key
            return (
                figures[0],
                figures[1],
                figures[2],
                figures[3],
                updated_generation_keys,
            )

    def _add_legend_change_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.LEGEND_DATA_STORE), "data"),
            Input(self._view_component(MapViewElement.Ids.BAR_PLOT), "restyleData"),
            State(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            Input(self._view_component(MapViewElement.Ids.TIME_PLOT), "restyleData"),
            State(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            Input(
                self._view_component(MapViewElement.Ids.PROBABILITY_PLOT), "restyleData"
            ),
            State(self._view_component(MapViewElement.Ids.PROBABILITY_PLOT), "figure"),
            Input(self._view_component(MapViewElement.Ids.BOX_PLOT), "restyleData"),
            State(self._view_component(MapViewElement.Ids.BOX_PLOT), "figure"),
        )
        def on_bar_legend_update(
            bar_event: List[Any],
            bar_figure: go.Figure,
            time_event: List[Any],
            time_figure: go.Figure,
            probability_event: List[Any],
            probability_figure: go.Figure,
            box_event: List[Any],
            box_figure: go.Figure,
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
            elif _id == self._view_component(MapViewElement.Ids.PROBABILITY_PLOT):
                if self._is_legend_click_event(probability_event):
                    p["probability_legendonly"] = extract_legendonly(probability_figure)
            elif _id == self._view_component(MapViewElement.Ids.BOX_PLOT):
                if self._is_legend_click_event(box_event):
                    p["box_legendonly"] = extract_legendonly(box_figure)
            return p

    @staticmethod
    def _is_legend_click_event(event: List[Any]) -> bool:
        # A typical legend click event would be: [{'visible': ['legendonly']}, [1]]
        if event is None or not isinstance(event, list):
            return False
        return any("visible" in e for e in event if isinstance(e, dict))

    def _add_csv_export_callback(self) -> None:
        @callback(
            Output(self._view_component(MapViewElement.Ids.DOWNLOAD_CSV), "data"),
            Input(
                self._view_component(MapViewElement.Ids.CSV_EXPORT_BUTTON), "n_clicks"
            ),
            State(self._view_component(MapViewElement.Ids.SUMMARY_TABS), "value"),
            State(self._view_component(MapViewElement.Ids.BAR_PLOT), "figure"),
            State(self._view_component(MapViewElement.Ids.TIME_PLOT), "figure"),
            State(self._view_component(MapViewElement.Ids.PROBABILITY_PLOT), "figure"),
            State(self._view_component(MapViewElement.Ids.BOX_PLOT), "figure"),
            prevent_initial_call=True,
        )
        def export_data(
            _n_clicks: int,
            active_tab: str,
            bar_figure: go.Figure,
            time_figure: go.Figure,
            probability_figure: go.Figure,
            box_figure: go.Figure,
        ) -> Dict[str, Any]:
            file_name = "co2_migration"
            if active_tab == MainTabOption.CONTAINMENT_STATE:
                current_figure = bar_figure
                file_name += "_state_plot"
                plot_choice = "containment_state"
            elif active_tab == MainTabOption.CONTAINMENT_OVER_TIME:
                current_figure = time_figure
                file_name += "_time_plot"
                plot_choice = "containment_time"
            elif active_tab == MainTabOption.PROBABILITY:
                current_figure = probability_figure
                file_name += "_probability_plot"
                plot_choice = "probability"
            elif active_tab == MainTabOption.BOX_PLOT:
                current_figure = box_figure
                file_name += "_box_plot"
                plot_choice = "box"
            else:
                raise PreventUpdate  # Should not happen

            date_and_time = datetime.now().strftime("%y%m%d_%H%M%S")
            file_name += f"_{date_and_time}.csv"
            result = export_figure_data_to_csv(current_figure, file_name, plot_choice)

            if result is None:
                raise PreventUpdate
            return result
