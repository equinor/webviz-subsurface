# pylint: disable=too-many-lines
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Input, NoUpdate, Output, State, callback, dcc, html, no_update
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    SurfaceStatistic,
)
from webviz_subsurface.plugins._co2_migration._utilities.callbacks import (
    property_origin,
)
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    FilteredMapAttribute,
    GraphSource,
    LayoutLabels,
    LayoutStyle,
    MapAttribute,
    MapGroup,
    MapThresholds,
    MapType,
    MenuOptions,
    map_group_labels,
)

ROW = {"display": "flex", "flex-direction": "row"}
COL = {"display": "flex", "flex-direction": "column"}
HIDDEN = {"display": "none"}
FILL = {"flex": 1}
LABEL = {"width": "75px", "flexShrink": 0, "alignSelf": "center"}
WIDE_LABEL = {**LABEL, "width": "145px", "whiteSpace": "nowrap"}
GRAPH_LABEL = {**LABEL, "width": "70px"}
SECTION = {"fontWeight": "bold", "marginTop": "8px"}
ROWS = {**COL, "gap": "4px"}


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        OVERLAY_DIALOG_BUTTON = "overlay-dialog-button"
        OVERLAY_DIALOG = "overlay-dialog"
        OVERLAY_DIALOG_OPTIONS = "overlay-dialog-options"
        OVERLAY_DIALOG_WELL_FILTER = "overlay-dialog-well-filter"
        WELL_FILTER_HEADER = "well-filter-header"

        ENSEMBLE = "ensemble"
        REALIZATION = "realization"
        ALL_REAL = "all-realizations"

        SETTINGS_TABS = "settings-tabs"

        FORMATION = "formation"  # Displayed as Zone in the UI
        PROPERTY = "property"
        STATISTIC = "statistic"
        STATISTIC_ROW = "statistic-row"
        COLOR_SCALE = "color-scale"
        CM_MIN = "cm-min"
        CM_MAX = "cm-max"
        CM_MIN_AUTO = "cm-min-auto"
        CM_MAX_AUTO = "cm-max-auto"
        MASS = "mass"
        MASS_UNIT = "mass-unit"
        CONTOURS_SWITCH = "contours-switch"
        CONTOURS_QUANTITY = "contours-quantity"
        PLUME = "plume"
        PLUME_THRESHOLD = "plume-threshold"
        PLUME_SMOOTHING = "plume-smoothing"

        GRAPH_SOURCE = "graph-source"
        CO2_SCALE = "co2-scale"
        Y_MIN_GRAPH = "y-min-graph"
        Y_MAX_GRAPH = "y-max-graph"
        Y_MIN_AUTO_GRAPH = "y-min-auto-graph"
        Y_MAX_AUTO_GRAPH = "y-max-auto-graph"
        Y_LIM_OPTIONS = "y_limit_options"
        COLOR_BY = "color-by"
        MARK_BY = "mark-by"
        SORT_PLOT = "sort-plot"
        ZONE = "zone"
        ZONE_COL = "zone-column"
        REGION_COL = "region-column"
        ZONE_REGION = "zone-and-region"
        REGION = "region"
        PHASE = "phase"
        PHASE_MENU = "phase-menu"
        CONTAINMENT = "containment"
        PLUME_GROUP = "plume-group"
        CONTAINMENT_MENU = "containment-menu"
        PLUME_GROUP_MENU = "plume-group-menu"
        GRAPH_FILTER_HEADER = "filter-header"
        GRAPH_DISPLAY_HEADER = "graph-display-header"

        VISUALIZATION_THRESHOLD_BUTTON = "visualization-threshold-button"
        VISUALIZATION_THRESHOLD_DIALOG = "visualization-threshold-dialog"

        FEEDBACK_BUTTON = "feedback-button"
        FEEDBACK = "feedback"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        ensemble_paths: Dict[str, str],
        realizations_per_ensemble: Dict[str, List[int]],
        ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
        initial_surface: Optional[str],
        map_attribute_names: FilteredMapAttribute,
        map_thresholds: MapThresholds,
        color_scale_names: List[str],
        well_names_dict: Dict[str, List[str]],
        menu_options: Dict[str, Dict[GraphSource, MenuOptions]],
        content: Dict[str, bool],
    ):
        super().__init__("Settings")
        self._ensemble_paths = ensemble_paths
        self._realizations_per_ensemble = realizations_per_ensemble
        self._ensemble_surface_providers = ensemble_surface_providers
        self._map_attribute_names = map_attribute_names
        self._thresholds = map_thresholds
        self._threshold_ids = list(self._thresholds.standard_thresholds.keys())
        self._color_scale_names = color_scale_names
        self._initial_surface = initial_surface
        self._well_names_dict = well_names_dict
        self._menu_options = menu_options
        self._content = content

    def layout(self) -> List[Component]:
        menu_layout: List[Component] = []
        if self._content["maps"]:
            menu_layout.append(
                OverlayDialogLayout(
                    self._well_names_dict, list(self._ensemble_paths.keys())
                )
            )
        menu_layout.append(
            EnsembleSelectorLayout(
                self.register_component_unique_id(self.Ids.ENSEMBLE),
                self.register_component_unique_id(self.Ids.REALIZATION),
                self.register_component_unique_id(self.Ids.ALL_REAL),
                list(self._ensemble_paths.keys()),
            )
        )
        tabs: List[Component] = []
        if self._content["maps"]:
            menu_layout.append(
                VisualizationThresholdsLayout(
                    self._threshold_ids,
                    self._thresholds,
                )
            )
            map_settings = MapSelectorLayout(
                self._color_scale_names,
                self.register_component_unique_id(self.Ids.PROPERTY),
                self.register_component_unique_id(self.Ids.STATISTIC),
                self.register_component_unique_id(self.Ids.STATISTIC_ROW),
                self.register_component_unique_id(self.Ids.FORMATION),
                self.register_component_unique_id(self.Ids.COLOR_SCALE),
                self.register_component_unique_id(self.Ids.CM_MIN),
                self.register_component_unique_id(self.Ids.CM_MAX),
                self.register_component_unique_id(self.Ids.CM_MIN_AUTO),
                self.register_component_unique_id(self.Ids.CM_MAX_AUTO),
                self.register_component_unique_id(self.Ids.CONTOURS_SWITCH),
                self.register_component_unique_id(self.Ids.CONTOURS_QUANTITY),
                self.register_component_unique_id(self.Ids.MASS),
                self.register_component_unique_id(self.Ids.MASS_UNIT),
                self.register_component_unique_id(self.Ids.PLUME),
                self.register_component_unique_id(self.Ids.PLUME_THRESHOLD),
                self.register_component_unique_id(self.Ids.PLUME_SMOOTHING),
                self._map_attribute_names,
            )
            tabs.append(
                wcc.Tab(label="Map settings", value="map", children=[map_settings])
            )
        if self._content["any_table"]:
            graph_settings = GraphSelectorsLayout(
                self.register_component_unique_id(self.Ids.GRAPH_SOURCE),
                self.register_component_unique_id(self.Ids.CO2_SCALE),
                [
                    self.register_component_unique_id(self.Ids.Y_MIN_GRAPH),
                    self.register_component_unique_id(self.Ids.Y_MIN_AUTO_GRAPH),
                ],
                [
                    self.register_component_unique_id(self.Ids.Y_MAX_GRAPH),
                    self.register_component_unique_id(self.Ids.Y_MAX_AUTO_GRAPH),
                ],
                {
                    k: self.register_component_unique_id(k)
                    for k in [
                        self.Ids.COLOR_BY,
                        self.Ids.MARK_BY,
                        self.Ids.SORT_PLOT,
                        self.Ids.ZONE,
                        self.Ids.ZONE_COL,
                        self.Ids.REGION,
                        self.Ids.REGION_COL,
                        self.Ids.ZONE_REGION,
                        self.Ids.PHASE,
                        self.Ids.PHASE_MENU,
                        self.Ids.CONTAINMENT,
                        self.Ids.CONTAINMENT_MENU,
                        self.Ids.PLUME_GROUP,
                        self.Ids.PLUME_GROUP_MENU,
                        self.Ids.Y_LIM_OPTIONS,
                        self.Ids.GRAPH_FILTER_HEADER,
                        self.Ids.GRAPH_DISPLAY_HEADER,
                    ]
                },
                self._content,
            )
            tabs.append(
                wcc.Tab(
                    label="Graph settings", value="graph", children=[graph_settings]
                )
            )
        if len(tabs) > 1:
            menu_layout.append(
                wcc.Tabs(
                    id=self.register_component_unique_id(self.Ids.SETTINGS_TABS),
                    value="map",
                    children=tabs,
                )
            )
        else:
            menu_layout += [c for tab in tabs for c in tab.children]
        menu_layout += [
            FeedbackLayout(),
            FeedbackButton(),
        ]
        return menu_layout

    # pylint: disable=too-many-statements
    def set_callbacks(self) -> None:
        # pylint: disable=unused-argument
        @callback(
            Output(
                self.component_unique_id(self.Ids.REALIZATION).to_string(), "options"
            ),
            Output(self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.ALL_REAL).to_string(), "n_clicks"),
        )
        def set_realizations(
            ensemble: str,
            select_all: int,
        ) -> Tuple[List[Dict[str, Any]], List[int]]:
            realizations = self._realizations_per_ensemble[ensemble]
            return [{"value": r, "label": str(r)} for r in realizations], realizations  # type: ignore

        @callback(
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
            State(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATION).to_string(), "value"),
        )
        def set_formations(
            prop: str, ensemble: str, current_value: str
        ) -> Tuple[List[Dict[str, Any]], Optional[Union[str, NoUpdate]]]:
            if ensemble is None:
                return [], None
            surface_provider = self._ensemble_surface_providers[ensemble]
            # Map
            prop_name = property_origin(MapAttribute(prop), self._map_attribute_names)
            surfaces = surface_provider.surface_names_for_attribute(prop_name)
            if len(surfaces) == 0:
                warning = f"Surface not found for property: {prop}.\n"
                warning += f"Expected name: <zone>--{prop_name}"
                if MapType[MapAttribute(prop).name].value != "MIGRATION_TIME":
                    warning += "--<date>"
                warnings.warn(warning + ".gri")
            # Formation names
            formations = [{"label": v.title(), "value": v} for v in surfaces]
            picked_formation: Optional[Union[str, NoUpdate]] = None
            if len(formations) != 0:
                if current_value is None and self._initial_surface in surfaces:
                    picked_formation = self._initial_surface
                elif current_value in surfaces:
                    picked_formation = no_update
                else:
                    picked_formation = (
                        "all"
                        if any((x["value"] == "all" for x in formations))
                        else formations[0]["value"]
                    )
            return formations, picked_formation

        if self._content["maps"]:

            @callback(
                Output(
                    self.component_unique_id(self.Ids.STATISTIC).to_string(), "disabled"
                ),
                Input(
                    self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"
                ),
            )
            def toggle_statistics(realizations: List[int]) -> bool:
                return len(realizations) <= 1

            @callback(
                Output(
                    self.component_unique_id(self.Ids.CM_MIN).to_string(), "disabled"
                ),
                Output(
                    self.component_unique_id(self.Ids.CM_MAX).to_string(), "disabled"
                ),
                Input(
                    self.component_unique_id(self.Ids.CM_MIN_AUTO).to_string(), "value"
                ),
                Input(
                    self.component_unique_id(self.Ids.CM_MAX_AUTO).to_string(), "value"
                ),
            )
            def set_color_range_data(
                min_auto: List[str], max_auto: List[str]
            ) -> Tuple[bool, bool]:
                return len(min_auto) == 1, len(max_auto) == 1

            @callback(
                Output(self.component_unique_id(self.Ids.MASS).to_string(), "style"),
                Output(self.component_unique_id(self.Ids.PLUME).to_string(), "style"),
                Output(
                    self.component_unique_id(self.Ids.STATISTIC_ROW).to_string(),
                    "style",
                ),
                Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
            )
            def toggle_property_specific_settings(
                attribute: str,
            ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
                map_type = MapType[MapAttribute(attribute).name].value
                return (
                    ROW if map_type == "MASS" else HIDDEN,
                    ROWS if map_type == "PLUME" else HIDDEN,
                    HIDDEN if map_type == "PLUME" else ROW,
                )

        if self._content["any_table"]:

            @callback(
                Output(
                    self.component_unique_id(self.Ids.Y_MIN_GRAPH).to_string(),
                    "disabled",
                ),
                Output(
                    self.component_unique_id(self.Ids.Y_MAX_GRAPH).to_string(),
                    "disabled",
                ),
                Input(
                    self.component_unique_id(self.Ids.Y_MIN_AUTO_GRAPH).to_string(),
                    "value",
                ),
                Input(
                    self.component_unique_id(self.Ids.Y_MAX_AUTO_GRAPH).to_string(),
                    "value",
                ),
            )
            def set_y_min_max(
                min_auto: List[str], max_auto: List[str]
            ) -> Tuple[bool, bool]:
                return len(min_auto) == 1, len(max_auto) == 1

            @callback(
                Output(self.component_unique_id(self.Ids.PHASE).to_string(), "options"),
                Output(self.component_unique_id(self.Ids.PHASE).to_string(), "value"),
                Input(
                    self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"
                ),
                Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
                State(self.component_unique_id(self.Ids.PHASE).to_string(), "value"),
            )
            def set_phases(
                source: GraphSource,
                ensemble: str,
                current_value: str,
            ) -> Tuple[List[Dict[str, str]], Union[Any, str]]:
                if ensemble is not None:
                    phases = self._menu_options[ensemble][source]["phases"]
                    options = [
                        {"label": phase.title(), "value": phase} for phase in phases
                    ]
                    return options, no_update if current_value in phases else "total"
                return [{"label": "Total", "value": "total"}], "total"

            @callback(
                Output(self.component_unique_id(self.Ids.ZONE).to_string(), "options"),
                Output(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
                Input(
                    self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"
                ),
                Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
                State(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            )
            def set_zones(
                source: GraphSource,
                ensemble: str,
                current_value: str,
            ) -> Tuple[List[Dict[str, str]], Union[Any, str]]:
                if ensemble is not None:
                    zones = self._menu_options[ensemble][source]["zones"]
                    if len(zones) > 0:
                        options = [
                            {"label": zone.title(), "value": zone} for zone in zones
                        ]
                        return options, no_update if current_value in zones else "all"
                return [{"label": "All", "value": "all"}], "all"

            @callback(
                Output(
                    self.component_unique_id(self.Ids.REGION).to_string(), "options"
                ),
                Output(self.component_unique_id(self.Ids.REGION).to_string(), "value"),
                Input(
                    self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"
                ),
                Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
                State(self.component_unique_id(self.Ids.REGION).to_string(), "value"),
            )
            def set_regions(
                source: GraphSource,
                ensemble: str,
                current_value: str,
            ) -> Tuple[List[Dict[str, str]], Union[Any, str]]:
                if ensemble is not None:
                    regions = self._menu_options[ensemble][source]["regions"]
                    if len(regions) > 0:
                        options = [
                            {"label": reg.title(), "value": reg} for reg in regions
                        ]
                        return options, no_update if current_value in regions else "all"
                return [{"label": "All", "value": "all"}], "all"

            @callback(
                Output(
                    self.component_unique_id(self.Ids.PLUME_GROUP).to_string(),
                    "options",
                ),
                Output(
                    self.component_unique_id(self.Ids.PLUME_GROUP).to_string(), "value"
                ),
                Input(
                    self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"
                ),
                Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
                State(
                    self.component_unique_id(self.Ids.PLUME_GROUP).to_string(), "value"
                ),
            )
            def set_plume_groups(
                source: GraphSource,
                ensemble: str,
                current_value: str,
            ) -> Tuple[List[Dict[str, str]], Union[Any, str]]:
                if ensemble is not None:
                    plume_groups = self._menu_options[ensemble][source]["plume_groups"]
                    if len(plume_groups) > 0:
                        options = [
                            {"label": x.title(), "value": x} for x in plume_groups
                        ]
                        return (
                            options,
                            no_update if current_value in plume_groups else "all",
                        )
                return [{"label": "All", "value": "all"}], "all"

            @callback(
                Output(
                    self.component_unique_id(self.Ids.MARK_BY).to_string(), "options"
                ),
                Output(self.component_unique_id(self.Ids.MARK_BY).to_string(), "value"),
                Output(
                    self.component_unique_id(self.Ids.ZONE_COL).to_string(), "style"
                ),
                Output(
                    self.component_unique_id(self.Ids.REGION_COL).to_string(), "style"
                ),
                Output(
                    self.component_unique_id(self.Ids.PHASE_MENU).to_string(), "style"
                ),
                Output(
                    self.component_unique_id(self.Ids.CONTAINMENT_MENU).to_string(),
                    "style",
                ),
                Output(
                    self.component_unique_id(self.Ids.PLUME_GROUP_MENU).to_string(),
                    "style",
                ),
                Input(self.component_unique_id(self.Ids.COLOR_BY).to_string(), "value"),
                Input(self.component_unique_id(self.Ids.MARK_BY).to_string(), "value"),
            )
            def organize_color_and_mark_menus(
                color_choice: str,
                mark_choice: str,
            ) -> Tuple[List[Dict], str, Dict, Dict, Dict, Dict, Dict]:
                mark_options = [{"label": "None", "value": "none"}]

                if color_choice != "containment":
                    mark_options.append(
                        {"label": "Containment", "value": "containment"}
                    )
                if color_choice != "phase":
                    mark_options.append({"label": "Phase", "value": "phase"})
                if color_choice not in ["zone", "region"] and self._content["zones"]:
                    mark_options.append({"label": "Zone", "value": "zone"})
                if color_choice not in ["zone", "region"] and self._content["regions"]:
                    mark_options.append({"label": "Region", "value": "region"})
                if color_choice != "plume_group" and self._content["plume_groups"]:
                    mark_options.append(
                        {"label": "Plume group", "value": "plume_group"}
                    )

                if mark_choice is None or mark_choice == color_choice:
                    if color_choice != "phase":
                        mark_choice = "phase"
                    else:
                        mark_choice = "containment"
                if mark_choice in ["zone", "region"] and color_choice in [
                    "zone",
                    "region",
                ]:
                    mark_choice = "phase"

                zone, region, phase, containment, plume_group = _make_styles(
                    color_choice,
                    mark_choice,
                    self._content["zones"],
                    self._content["regions"],
                    self._content["plume_groups"],
                )
                return (
                    mark_options,
                    mark_choice,
                    zone,
                    region,
                    phase,
                    containment,
                    plume_group,
                )

            @callback(
                Output(self.component_unique_id(self.Ids.ZONE).to_string(), "disabled"),
                Output(
                    self.component_unique_id(self.Ids.REGION).to_string(), "disabled"
                ),
                Input(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
                Input(self.component_unique_id(self.Ids.REGION).to_string(), "value"),
            )
            def disable_zone_or_region(zone: str, region: str) -> Tuple[bool, bool]:
                return region != "all", zone != "all"

            @callback(
                Output(
                    self.component_unique_id(self.Ids.GRAPH_FILTER_HEADER).to_string(),
                    "style",
                ),
                [
                    Input(self.component_unique_id(i).to_string(), "style")
                    for i in (
                        self.Ids.ZONE_COL,
                        self.Ids.REGION_COL,
                        self.Ids.PHASE_MENU,
                        self.Ids.CONTAINMENT_MENU,
                        self.Ids.PLUME_GROUP_MENU,
                    )
                ],
            )
            def toggle_filter_header(
                *filter_styles: Optional[Dict[str, str]]
            ) -> Dict[str, str]:
                any_visible = any(
                    (style or {}).get("display") != "none" for style in filter_styles
                )
                return SECTION if any_visible else HIDDEN


class OpenOverlayDialogButton(html.Button):
    def __init__(self) -> None:
        super().__init__(
            LayoutLabels.OVERLAY_FILTER,
            id=ViewSettings.Ids.OVERLAY_DIALOG_BUTTON,
            style=LayoutStyle.OVERLAY_BUTTON,
            n_clicks=0,
        )


class OverlayDialogLayout(wcc.Dialog):
    """Layout for the overlay dialog"""

    def __init__(
        self,
        well_names_dict: Dict[str, List[str]],
        ensembles: List[str],
    ) -> None:
        checklist_values = [
            LayoutLabels.SHOW_FAULTPOLYGONS,
            LayoutLabels.SHOW_CONTAINMENT_POLYGON,
            LayoutLabels.SHOW_NOGO_POLYGON,
            LayoutLabels.SHOW_WELLS,
        ]
        checklist_options = [
            LayoutLabels.SHOW_FAULTPOLYGONS,
            LayoutLabels.SHOW_CONTAINMENT_POLYGON,
            LayoutLabels.SHOW_NOGO_POLYGON,
            LayoutLabels.SHOW_POLYGONS_AS_OUTLINES,
            LayoutLabels.SHOW_WELLS,
        ]

        super().__init__(
            title=LayoutLabels.OVERLAY_FILTER,
            id=ViewSettings.Ids.OVERLAY_DIALOG,
            draggable=True,
            open=False,
            children=[
                wcc.Checklist(
                    id=ViewSettings.Ids.OVERLAY_DIALOG_OPTIONS,
                    options=[{"label": opt, "value": opt} for opt in checklist_options],
                    value=checklist_values,
                ),
                wcc.FlexBox(
                    children=[
                        html.Div(
                            id=ViewSettings.Ids.WELL_FILTER_HEADER,
                            style={
                                "flex": 3,
                                "minWidth": "20px",
                                "display": (
                                    "block" if well_names_dict[ensembles[0]] else "none"
                                ),
                            },
                            children=WellFilter(well_names_dict, ensembles),
                        ),
                    ],
                    style={"width": "20vw"},
                ),
            ],
        )


class WellFilter(html.Div):
    def __init__(
        self, well_names_dict: Dict[str, List[str]], ensembles: List[str]
    ) -> None:
        super().__init__(
            children=wcc.SelectWithLabel(
                style={"display": "block" if well_names_dict[ensembles[0]] else "none"},
                label=LayoutLabels.WELL_FILTER,
                id=ViewSettings.Ids.OVERLAY_DIALOG_WELL_FILTER,
                options=[
                    {"label": i, "value": i} for i in well_names_dict[ensembles[0]]
                ],
                value=well_names_dict[ensembles[0]],
                size=min(20, len(well_names_dict[ensembles[0]])),
            ),
        )


class OpenVisualizationThresholdsButton(html.Button):
    def __init__(self) -> None:
        super().__init__(
            LayoutLabels.VISUALIZATION_THRESHOLDS,
            id=ViewSettings.Ids.VISUALIZATION_THRESHOLD_BUTTON,
            style=LayoutStyle.THRESHOLDS_BUTTON,
            n_clicks=0,
        )


class VisualizationThresholdsLayout(wcc.Dialog):
    """Layout for the visualization thresholds dialog"""

    def __init__(
        self,
        ids: List[str],
        thresholds: MapThresholds,
    ) -> None:
        standard_thresholds = thresholds.standard_thresholds

        fields = [
            html.Div(
                "Here you can select a filter for the visualization of the map, "
                "hiding values smaller than the selected minimum cutoff. "
                "A value of -1 can be used to visualize zeros."
            ),
            html.Div("", style={"height": "30px"}),
            html.Div(
                [
                    html.Div("Property:", style={"width": "42%"}),
                    html.Div("Standard cutoff:", style={"width": "32%"}),
                    html.Div("Minimum cutoff:", style={"width": "25%"}),
                ],
                style=ROW,
            ),
        ]
        fields += [
            html.Div(
                [
                    html.Div(id, style={"width": "42%"}),
                    html.Div(standard_thresholds[id], style={"width": "32%"}),
                    dcc.Input(
                        id=id,
                        type="number",
                        value=standard_thresholds[id],
                        step="0.0005",
                        debounce=True,
                        style={"width": "25%"},
                    ),
                ],
                style=ROW,
            )
            for id in ids
        ]
        super().__init__(
            title=LayoutLabels.VISUALIZATION_THRESHOLDS,
            id=ViewSettings.Ids.VISUALIZATION_THRESHOLD_DIALOG,
            draggable=True,
            open=False,
            children=html.Div(fields, style={**COL, "width": "600px"}),
        )


class MapSelectorLayout(html.Div):
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        color_scale_names: List[str],
        property_id: str,
        statistic_id: str,
        statistic_row_id: str,
        formation_id: str,
        colormap_id: str,
        cm_min_id: str,
        cm_max_id: str,
        cm_min_auto_id: str,
        cm_max_auto_id: str,
        contour_switch_id: str,
        contour_quantity_id: str,
        mass_id: str,
        mass_unit_id: str,
        plume_id: str,
        plume_threshold_id: str,
        plume_smoothing_id: str,
        map_attribute_names: FilteredMapAttribute,
    ):
        default_colormap = (
            "turbo (Seq)"
            if "turbo (Seq)" in color_scale_names
            else color_scale_names[0]
        )
        default_property = next(iter(map_attribute_names.filtered_values)).value
        default_map_type = MapType[MapAttribute(default_property).name].value
        super().__init__(
            children=[
                html.Div(
                    [
                        html.Div("Data", style=SECTION),
                        html.Div(
                            [
                                html.Div("Property", style=LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        id=property_id,
                                        options=_compile_property_options(
                                            map_attribute_names
                                        ),
                                        value=default_property,
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div(
                            [
                                html.Div("Unit", style=LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        id=mass_unit_id,
                                        options=["kg", "tons", "M tons"],
                                        value="tons",
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=mass_id,
                            style=(ROW if default_map_type == "MASS" else HIDDEN),
                        ),
                        html.Div(
                            [
                                html.Div("Statistic", style=LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        id=statistic_id,
                                        options=[s.value for s in SurfaceStatistic],
                                        value=SurfaceStatistic.MEAN,
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=statistic_row_id,
                            style=(HIDDEN if default_map_type == "PLUME" else ROW),
                        ),
                        html.Div("Filter", style=SECTION),
                        html.Div(
                            [
                                html.Div("Zone", style=LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        id=formation_id,
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div("Display", style=SECTION),
                        html.Div(
                            [
                                html.Div("Colormap", style=LABEL),
                                dcc.Dropdown(
                                    id=colormap_id,
                                    options=color_scale_names,
                                    value=default_colormap,
                                    clearable=False,
                                    style=FILL,
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div(
                            [
                                html.Div("Minimum", style=LABEL),
                                dcc.Input(
                                    id=cm_min_id,
                                    type="number",
                                    style={"flex": 1, "minWidth": 0},
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_min_auto_id,
                                    style={"whiteSpace": "nowrap"},
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div(
                            [
                                html.Div("Maximum", style=LABEL),
                                dcc.Input(
                                    id=cm_max_id,
                                    type="number",
                                    style={"flex": 1, "minWidth": 0},
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_max_auto_id,
                                    style={"whiteSpace": "nowrap"},
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div(
                            [
                                html.Div("Contours", style=LABEL),
                                "#",
                                dcc.Input(
                                    id=contour_quantity_id,
                                    value=5,
                                    type="number",
                                    min=1,
                                    style={"width": "25%"},
                                ),
                                dcc.Checklist(
                                    ["On/Off"],
                                    [],
                                    id=contour_switch_id,
                                ),
                            ],
                            style=ROW,
                            title=(
                                "Contours work best with relatively smooth maps,"
                                " and Minimum and Maximum set to 'auto'."
                            ),
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    [
                                        html.Div("Plume threshold", style=WIDE_LABEL),
                                        dcc.Input(
                                            id=plume_threshold_id,
                                            type="number",
                                            min=0,
                                            value=0.000001,
                                            placeholder="Lower property threshold",
                                            style={"flex": 1, "minWidth": 0},
                                        ),
                                    ],
                                    style=ROW,
                                ),
                                html.Div(
                                    [
                                        html.Div("Plume smoothing", style=WIDE_LABEL),
                                        dcc.Input(
                                            id=plume_smoothing_id,
                                            type="number",
                                            min=0,
                                            value=0,
                                            step=1,
                                            placeholder="Smoothing [#pixels]",
                                            style={"flex": 1, "minWidth": 0},
                                        ),
                                    ],
                                    style=ROW,
                                ),
                            ],
                            id=plume_id,
                            style=(ROWS if default_map_type == "PLUME" else HIDDEN),
                        ),
                        OpenOverlayDialogButton(),
                        OpenVisualizationThresholdsButton(),
                    ],
                    style=ROWS,
                ),
            ],
        )


class GraphSelectorsLayout(html.Div):
    # pylint: disable=too-many-locals
    def __init__(
        self,
        graph_source_id: str,
        co2_scale_id: str,
        y_min_ids: List[str],
        y_max_ids: List[str],
        containment_ids: Dict[str, str],  # ViewSettings.Ids
        content: Dict[str, bool],
    ):
        color_choice = "containment"
        mark_choice = "phase"
        zone_style, region_style, phase_style, cont_style, plume_style = _make_styles(
            color_choice,
            mark_choice,
            content["zones"],
            content["regions"],
            content["plume_groups"],
        )
        cont_option = {"label": "Containment", "value": "containment"}
        phase_option = {"label": "Phase", "value": "phase"}
        color_options = [cont_option, phase_option]
        mark_options = [phase_option, cont_option]

        optional = [
            ("zones", {"label": "Zone", "value": "zone"}),
            ("regions", {"label": "Region", "value": "region"}),
            ("plume_groups", {"label": "Plume group", "value": "plume_group"}),
        ]

        for key, opt in optional:
            if content[key]:
                color_options.append(opt)
                mark_options.append(opt)

        source_options = []
        if content["mass"]:
            source_options.append(GraphSource.CONTAINMENT_MASS)
        if content["volume"]:
            source_options.append(GraphSource.CONTAINMENT_ACTUAL_VOLUME)
        if content["unsmry"]:
            source_options.append(GraphSource.UNSMRY)
        unit_options, init_unit = (
            (list(Co2VolumeScale), Co2VolumeScale.BILLION_CUBIC_METERS)
            if source_options[0] == GraphSource.CONTAINMENT_ACTUAL_VOLUME
            else (list(Co2MassScale), Co2MassScale.MTONS)
        )
        ids = ViewSettings.Ids
        super().__init__(
            style=ROWS,
            children=[
                html.Div("Data", style=SECTION),
                html.Div(
                    [
                        html.Div("Source", style=GRAPH_LABEL),
                        html.Div(
                            wcc.Dropdown(
                                id=graph_source_id,
                                options=source_options,
                                value=source_options[0],
                                clearable=False,
                            ),
                            style=FILL,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div(
                    [
                        html.Div("Unit", style=GRAPH_LABEL),
                        html.Div(
                            wcc.Dropdown(
                                id=co2_scale_id,
                                options=unit_options,
                                value=init_unit,
                                clearable=False,
                            ),
                            style=FILL,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div("Grouping", style=SECTION),
                html.Div(
                    [
                        html.Div("Color by", style=GRAPH_LABEL),
                        html.Div(
                            wcc.Dropdown(
                                options=color_options,
                                value=color_choice,
                                id=containment_ids[ids.COLOR_BY],
                                clearable=False,
                            ),
                            style=FILL,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div(
                    [
                        html.Div("Mark by", style=GRAPH_LABEL),
                        html.Div(
                            wcc.Dropdown(
                                options=mark_options,
                                value=mark_choice,
                                id=containment_ids[ids.MARK_BY],
                                clearable=False,
                            ),
                            style=FILL,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div(
                    [
                        html.Div("Sort by", style=GRAPH_LABEL),
                        dcc.RadioItems(
                            options=[
                                {"label": "colors", "value": "color"},
                                {"label": "marks", "value": "marking"},
                            ],
                            value="color",
                            id=containment_ids[ids.SORT_PLOT],
                            inline=True,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div(
                    "Filter",
                    id=containment_ids[ids.GRAPH_FILTER_HEADER],
                    style=SECTION,
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Zone", style=GRAPH_LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        options=[{"label": "All", "value": "all"}],
                                        value="all",
                                        id=containment_ids[ids.ZONE],
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=containment_ids[ids.ZONE_COL],
                            style=zone_style,
                        ),
                        html.Div(
                            [
                                html.Div("Region", style=GRAPH_LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        options=[{"label": "All", "value": "all"}],
                                        value="all",
                                        id=containment_ids[ids.REGION],
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=containment_ids[ids.REGION_COL],
                            style=region_style,
                        ),
                        html.Div(
                            [
                                html.Div("Phase", style=GRAPH_LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        options=[{"label": "Total", "value": "total"}],
                                        value="total",
                                        clearable=False,
                                        id=containment_ids[ids.PHASE],
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=containment_ids[ids.PHASE_MENU],
                            style=phase_style,
                        ),
                        html.Div(
                            [
                                html.Div(
                                    "Containment",
                                    style={**GRAPH_LABEL, "width": "95px"},
                                ),
                                html.Div(
                                    wcc.Dropdown(
                                        options=[
                                            {"label": "All areas", "value": "total"},
                                            {
                                                "label": "Contained",
                                                "value": "contained",
                                            },
                                            {"label": "Outside", "value": "outside"},
                                            {"label": "No-go", "value": "nogo"},
                                        ],
                                        value="total",
                                        clearable=False,
                                        id=containment_ids[ids.CONTAINMENT],
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=containment_ids[ids.CONTAINMENT_MENU],
                            style=cont_style,
                        ),
                        html.Div(
                            [
                                html.Div("Plume", style=GRAPH_LABEL),
                                html.Div(
                                    wcc.Dropdown(
                                        options=[{"label": "All", "value": "all"}],
                                        value="all",
                                        id=containment_ids[ids.PLUME_GROUP],
                                        clearable=False,
                                    ),
                                    style=FILL,
                                ),
                            ],
                            id=containment_ids[ids.PLUME_GROUP_MENU],
                            style=plume_style,
                        ),
                    ],
                    id=containment_ids[ids.ZONE_REGION],
                    style=ROWS,
                ),
                html.Div(
                    "Display",
                    id=containment_ids[ids.GRAPH_DISPLAY_HEADER],
                    style=HIDDEN,
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    "Y minimum",
                                    style={**GRAPH_LABEL, "width": "95px"},
                                ),
                                dcc.Input(
                                    id=y_min_ids[0],
                                    type="number",
                                    style={"flex": 1, "minWidth": 0},
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=y_min_ids[1],
                                    style={"whiteSpace": "nowrap"},
                                ),
                            ],
                            style=ROW,
                        ),
                        html.Div(
                            [
                                html.Div(
                                    "Y maximum",
                                    style={**GRAPH_LABEL, "width": "95px"},
                                ),
                                dcc.Input(
                                    id=y_max_ids[0],
                                    type="number",
                                    style={"flex": 1, "minWidth": 0},
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=y_max_ids[1],
                                    style={"whiteSpace": "nowrap"},
                                ),
                            ],
                            style=ROW,
                        ),
                    ],
                    style=HIDDEN,
                    id=containment_ids[ids.Y_LIM_OPTIONS],
                ),
            ],
        )


class EnsembleSelectorLayout(html.Div):
    def __init__(
        self,
        ensemble_id: str,
        realization_id: str,
        all_real_id: str,
        ensembles: List[str],
    ):
        super().__init__(
            style={"marginBottom": "10px"},
            children=[
                html.Div(
                    [
                        html.Div("Ensemble", style=WIDE_LABEL),
                        html.Div(
                            wcc.Dropdown(
                                id=ensemble_id,
                                options=[
                                    {"value": en, "label": en} for en in ensembles
                                ],
                                value=ensembles[0],
                                clearable=False,
                            ),
                            style=FILL,
                        ),
                    ],
                    style=ROW,
                ),
                html.Div(
                    [
                        html.Div("Realization", style=WIDE_LABEL),
                        html.Button(
                            "Select all",
                            id=all_real_id,
                            style=LayoutStyle.ALL_REAL_BUTTON,
                            n_clicks=0,
                        ),
                    ],
                    style={
                        **ROW,
                        "margin-top": "3px",
                        "margin-bottom": "3px",
                    },
                ),
                wcc.SelectWithLabel(
                    id=realization_id,
                    value=[],
                    multi=True,
                ),
            ],
        )


def _create_left_side_menu(
    map_group: str, map_attribute_names: FilteredMapAttribute
) -> List:
    title = {
        "label": html.Span([f"{map_group}:"], style={"text-decoration": "underline"}),
        "value": "",
        "disabled": True,
    }
    map_attribute_list = [
        {"label": MapAttribute[key.name].value, "value": MapAttribute[key.name].value}
        for key in map_attribute_names.filtered_values.keys()
        if map_group_labels[MapGroup[key.name].value] == map_group
    ]
    return [title] + map_attribute_list


def _compile_property_options(
    map_attribute_names: FilteredMapAttribute,
) -> List[Dict[str, Any]]:
    requested_map_groups = [
        map_group_labels[MapGroup[key.name].value]
        for key in map_attribute_names.filtered_values.keys()
    ]
    unique_requested_map_groups = list(set(requested_map_groups))
    return [
        element
        for group in unique_requested_map_groups
        for element in _create_left_side_menu(group, map_attribute_names)
    ]


class FeedbackLayout(wcc.Dialog):
    """Layout for the feedback button"""

    def __init__(
        self,
    ) -> None:
        super().__init__(
            title=LayoutLabels.FEEDBACK,
            id=ViewSettings.Ids.FEEDBACK,
            draggable=True,
            open=False,
            children=[
                dcc.Markdown(
                    """If you have any feedback regarding the CO2-Migration application,
                    don't hesitate to"""
                ),
                dcc.Link(
                    ["send an email!"],
                    href=f"mailto:{get_emails()}&subject=Feedback regarding the "
                    f"CO2-Migration application",
                    target="_blank",
                    style={"float": "left"},
                ),
            ],
        )


class FeedbackButton(html.Button):
    def __init__(self) -> None:
        style = LayoutStyle.FEEDBACK_BUTTON
        super().__init__(
            LayoutLabels.FEEDBACK,
            id=ViewSettings.Ids.FEEDBACK_BUTTON,
            style=style,
            n_clicks=0,
        )


def decrypt_email(encrypted_email: str, key: int) -> str:
    return "".join(chr(ord(char) ^ key) for char in encrypted_email)


def get_emails() -> str:
    emails = [
        decrypt_email(m, i + 1)
        for i, m in enumerate(
            [
                "GLLNAdpthons/bnl",
                "`ijBgswklmp,amo",
                "pfhCmq-ml",
                "bjarnajDjv*jk",
                "vlfdfmdEkw+kj",
            ]
        )
    ]
    return ";".join(emails[:2]) + "?cc=" + ";".join(emails[2:])


def _make_styles(
    color_choice: str,
    mark_choice: str,
    has_zones: bool,
    has_regions: bool,
    has_plume_groups: bool,
) -> List[Dict[str, str]]:
    cm = [color_choice, mark_choice]
    zone_or_region = "zone" in cm or "region" in cm  # Only one can be chosen

    possible_filters = [
        not zone_or_region and has_zones,
        not zone_or_region and has_regions,
        "phase" not in cm,  # We always have phases
        "containment" not in cm,  # We always have containment status
        "plume_group" not in cm and has_plume_groups,
    ]

    return [ROW if f else HIDDEN for f in possible_filters]
