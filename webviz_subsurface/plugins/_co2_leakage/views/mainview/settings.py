# pylint: disable=too-many-lines
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    SurfaceStatistic,
)
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import property_origin
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    GraphSource,
    LayoutLabels,
    LayoutStyle,
    MapAttribute,
)


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        OPTIONS_DIALOG_BUTTON = "options-dialog-button"
        OPTIONS_DIALOG = "options-dialog"
        OPTIONS_DIALOG_OPTIONS = "options-dialog-options"
        OPTIONS_DIALOG_WELL_FILTER = "options-dialog-well-filter"
        WELL_FILTER_HEADER = "well-filter-header"

        FORMATION = "formation"
        ENSEMBLE = "ensemble"
        REALIZATION = "realization"

        PROPERTY = "property"
        STATISTIC = "statistic"
        COLOR_SCALE = "color-scale"
        CM_MIN = "cm-min"
        CM_MAX = "cm-max"
        CM_MIN_AUTO = "cm-min-auto"
        CM_MAX_AUTO = "cm-max-auto"

        GRAPH_SOURCE = "graph-source"
        CO2_SCALE = "co2-scale"
        Y_MIN_GRAPH = "y-min-graph"
        Y_MAX_GRAPH = "y-max-graph"
        Y_MIN_AUTO_GRAPH = "y-min-auto-graph"
        Y_MAX_AUTO_GRAPH = "y-max-auto-graph"
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
        CONTAINMENT_MENU = "containment-menu"

        PLUME_THRESHOLD = "plume-threshold"
        PLUME_SMOOTHING = "plume-smoothing"

        VISUALIZATION_THRESHOLD = "visualization-threshold"
        VISUALIZATION_UPDATE = "visualization-update"
        MASS_UNIT = "mass-unit"

        FEEDBACK_BUTTON = "feedback-button"
        FEEDBACK = "feedback"

    def __init__(
        self,
        ensemble_paths: Dict[str, str],
        ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
        initial_surface: Optional[str],
        map_attribute_names: Dict[MapAttribute, str],
        color_scale_names: List[str],
        well_names_dict: Dict[str, List[str]],
        menu_options: Dict[str, Dict[str, Dict[str, List[str]]]],
    ):
        super().__init__("Settings")
        self._ensemble_paths = ensemble_paths
        self._ensemble_surface_providers = ensemble_surface_providers
        self._map_attribute_names = map_attribute_names
        self._color_scale_names = color_scale_names
        self._initial_surface = initial_surface
        self._well_names_dict = well_names_dict
        self._menu_options = menu_options
        self._has_zones = max(
            len(inner_dict["zones"]) > 0
            for outer_dict in menu_options.values()
            for inner_dict in outer_dict.values()
        )
        self._has_regions = max(
            len(inner_dict["regions"]) > 0
            for outer_dict in menu_options.values()
            for inner_dict in outer_dict.values()
        )

    def layout(self) -> List[Component]:
        return [
            DialogLayout(self._well_names_dict, list(self._ensemble_paths.keys())),
            OpenDialogButton(),
            EnsembleSelectorLayout(
                self.register_component_unique_id(self.Ids.ENSEMBLE),
                self.register_component_unique_id(self.Ids.REALIZATION),
                list(self._ensemble_paths.keys()),
            ),
            FilterSelectorLayout(self.register_component_unique_id(self.Ids.FORMATION)),
            MapSelectorLayout(
                self._color_scale_names,
                self.register_component_unique_id(self.Ids.PROPERTY),
                self.register_component_unique_id(self.Ids.STATISTIC),
                self.register_component_unique_id(self.Ids.COLOR_SCALE),
                self.register_component_unique_id(self.Ids.CM_MIN),
                self.register_component_unique_id(self.Ids.CM_MAX),
                self.register_component_unique_id(self.Ids.CM_MIN_AUTO),
                self.register_component_unique_id(self.Ids.CM_MAX_AUTO),
                self.register_component_unique_id(self.Ids.VISUALIZATION_THRESHOLD),
                self.register_component_unique_id(self.Ids.VISUALIZATION_UPDATE),
                self.register_component_unique_id(self.Ids.MASS_UNIT),
            ),
            GraphSelectorsLayout(
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
                [
                    self.register_component_unique_id(self.Ids.COLOR_BY),
                    self.register_component_unique_id(self.Ids.MARK_BY),
                    self.register_component_unique_id(self.Ids.SORT_PLOT),
                    self.register_component_unique_id(self.Ids.ZONE),
                    self.register_component_unique_id(self.Ids.ZONE_COL),
                    self.register_component_unique_id(self.Ids.REGION),
                    self.register_component_unique_id(self.Ids.REGION_COL),
                    self.register_component_unique_id(self.Ids.ZONE_REGION),
                    self.register_component_unique_id(self.Ids.PHASE),
                    self.register_component_unique_id(self.Ids.PHASE_MENU),
                    self.register_component_unique_id(self.Ids.CONTAINMENT),
                    self.register_component_unique_id(self.Ids.CONTAINMENT_MENU),
                ],
                self._has_zones,
                self._has_regions,
            ),
            ExperimentalFeaturesLayout(
                self.register_component_unique_id(self.Ids.PLUME_THRESHOLD),
                self.register_component_unique_id(self.Ids.PLUME_SMOOTHING),
            ),
            FeedbackLayout(),
            FeedbackButton(),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.REALIZATION).to_string(), "options"
            ),
            Output(self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
        )
        def set_realizations(ensemble: str) -> Tuple[List[Dict[str, Any]], List[int]]:
            rlz = [
                {"value": r, "label": str(r)}
                for r in self._ensemble_surface_providers[ensemble].realizations()
            ]
            return rlz, [rlz[0]["value"]]  # type: ignore

        @callback(
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
            State(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
            State(self.component_unique_id(self.Ids.FORMATION).to_string(), "value"),
        )
        def set_formations(
            prop: str, ensemble: str, current_value: str
        ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
            if ensemble is None:
                return [], None
            surface_provider = self._ensemble_surface_providers[ensemble]
            # Map
            prop_name = property_origin(MapAttribute(prop), self._map_attribute_names)
            surfaces = surface_provider.surface_names_for_attribute(prop_name)
            if len(surfaces) == 0:
                warning = f"Surface not found for property: {prop}.\n"
                warning += f"Expected name: <formation>--{prop_name}"
                if MapAttribute(prop) not in [
                    MapAttribute.MIGRATION_TIME_SGAS,
                    MapAttribute.MIGRATION_TIME_AMFG,
                ]:
                    warning += "--<date>"
                warnings.warn(warning + ".gri")
            # Formation names
            formations = [{"label": v.title(), "value": v} for v in surfaces]
            picked_formation = None
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

        @callback(
            Output(
                self.component_unique_id(self.Ids.STATISTIC).to_string(), "disabled"
            ),
            Input(self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
        )
        def toggle_statistics(realizations: List[int], attribute: str) -> bool:
            if len(realizations) <= 1:
                return True
            if MapAttribute(attribute) in (
                MapAttribute.SGAS_PLUME,
                MapAttribute.AMFG_PLUME,
            ):
                return True
            return False

        @callback(
            Output(self.component_unique_id(self.Ids.CM_MIN).to_string(), "disabled"),
            Output(self.component_unique_id(self.Ids.CM_MAX).to_string(), "disabled"),
            Input(self.component_unique_id(self.Ids.CM_MIN_AUTO).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.CM_MAX_AUTO).to_string(), "value"),
        )
        def set_color_range_data(
            min_auto: List[str], max_auto: List[str]
        ) -> Tuple[bool, bool]:
            return len(min_auto) == 1, len(max_auto) == 1

        @callback(
            Output(
                self.component_unique_id(self.Ids.VISUALIZATION_THRESHOLD).to_string(),
                "disabled",
            ),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
        )
        def set_visualization_threshold(attribute: str) -> bool:
            return MapAttribute(attribute) in [
                MapAttribute.MIGRATION_TIME_SGAS,
                MapAttribute.MIGRATION_TIME_AMFG,
            ]

        @callback(
            Output(
                self.component_unique_id(self.Ids.Y_MIN_GRAPH).to_string(), "disabled"
            ),
            Output(
                self.component_unique_id(self.Ids.Y_MAX_GRAPH).to_string(), "disabled"
            ),
            Input(
                self.component_unique_id(self.Ids.Y_MIN_AUTO_GRAPH).to_string(), "value"
            ),
            Input(
                self.component_unique_id(self.Ids.Y_MAX_AUTO_GRAPH).to_string(), "value"
            ),
        )
        def set_y_min_max(
            min_auto: List[str], max_auto: List[str]
        ) -> Tuple[bool, bool]:
            return len(min_auto) == 1, len(max_auto) == 1

        @callback(
            Output(self.component_unique_id(self.Ids.PHASE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.PHASE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"),
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
                options = [{"label": phase.title(), "value": phase} for phase in phases]
                return options, no_update if current_value in phases else "total"
            return [], "total"

        @callback(
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"),
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
                    options = [{"label": zone.title(), "value": zone} for zone in zones]
                    return options, no_update if current_value in zones else "all"
            return [], "all"

        @callback(
            Output(self.component_unique_id(self.Ids.REGION).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.REGION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.GRAPH_SOURCE).to_string(), "value"),
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
                    options = [{"label": reg.title(), "value": reg} for reg in regions]
                    return options, no_update if current_value in regions else "all"
            return [], "all"

        @callback(
            Output(
                self.component_unique_id(self.Ids.MASS_UNIT).to_string(), "disabled"
            ),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
        )
        def toggle_unit(attribute: str) -> bool:
            if MapAttribute(attribute) not in (
                MapAttribute.MASS,
                MapAttribute.FREE,
                MapAttribute.DISSOLVED,
            ):
                return True
            return False

        @callback(
            Output(self.component_unique_id(self.Ids.MARK_BY).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.MARK_BY).to_string(), "value"),
            Output(self.component_unique_id(self.Ids.ZONE_COL).to_string(), "style"),
            Output(self.component_unique_id(self.Ids.REGION_COL).to_string(), "style"),
            Output(self.component_unique_id(self.Ids.PHASE_MENU).to_string(), "style"),
            Output(
                self.component_unique_id(self.Ids.CONTAINMENT_MENU).to_string(),
                "style",
            ),
            Input(self.component_unique_id(self.Ids.COLOR_BY).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.MARK_BY).to_string(), "value"),
        )
        def organize_color_and_mark_menus(
            color_choice: str,
            mark_choice: str,
        ) -> Tuple[List[Dict], str, Dict, Dict, Dict, Dict]:
            mark_options = [
                {"label": "Phase", "value": "phase"},
                {"label": "None", "value": "none"},
            ]
            if self._has_zones and color_choice == "containment":
                mark_options.append({"label": "Zone", "value": "zone"})
            if self._has_regions and color_choice == "containment":
                mark_options.append({"label": "Region", "value": "region"})
            if color_choice in ["zone", "region"]:
                mark_options.append({"label": "Containment", "value": "containment"})
            if mark_choice is None or mark_choice == color_choice:
                mark_choice = "phase"
            if mark_choice in ["zone", "region"] and color_choice in ["zone", "region"]:
                mark_choice = "phase"
            zone, region, phase, containment = _make_styles(
                color_choice, mark_choice, self._has_zones, self._has_regions
            )
            return mark_options, mark_choice, zone, region, phase, containment

        @callback(
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "disabled"),
            Output(self.component_unique_id(self.Ids.REGION).to_string(), "disabled"),
            Input(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.REGION).to_string(), "value"),
        )
        def disable_zone_or_region(zone: str, region: str) -> Tuple[bool, bool]:
            return region != "all", zone != "all"


class OpenDialogButton(html.Button):
    def __init__(self) -> None:
        super().__init__(
            LayoutLabels.COMMON_SELECTIONS,
            id=ViewSettings.Ids.OPTIONS_DIALOG_BUTTON,
            style=LayoutStyle.OPTIONS_BUTTON,
            n_clicks=0,
        )


class DialogLayout(wcc.Dialog):
    """Layout for the options dialog"""

    def __init__(
        self,
        well_names_dict: Dict[str, List[str]],
        ensembles: List[str],
    ) -> None:
        checklist_options = []
        checklist_values = []
        checklist_options.append(LayoutLabels.SHOW_FAULTPOLYGONS)
        checklist_values.append(LayoutLabels.SHOW_FAULTPOLYGONS)
        checklist_options.append(LayoutLabels.SHOW_CONTAINMENT_POLYGON)
        checklist_values.append(LayoutLabels.SHOW_CONTAINMENT_POLYGON)
        checklist_options.append(LayoutLabels.SHOW_HAZARDOUS_POLYGON)
        checklist_values.append(LayoutLabels.SHOW_HAZARDOUS_POLYGON)
        checklist_options.append(LayoutLabels.SHOW_WELLS)
        checklist_values.append(LayoutLabels.SHOW_WELLS)

        super().__init__(
            title=LayoutLabels.COMMON_SELECTIONS,
            id=ViewSettings.Ids.OPTIONS_DIALOG,
            draggable=True,
            open=False,
            children=[
                wcc.Checklist(
                    id=ViewSettings.Ids.OPTIONS_DIALOG_OPTIONS,
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
                id=ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER,
                options=[
                    {"label": i, "value": i} for i in well_names_dict[ensembles[0]]
                ],
                value=well_names_dict[ensembles[0]],
                size=min(20, len(well_names_dict[ensembles[0]])),
            ),
        )


class FilterSelectorLayout(wcc.Selectors):
    def __init__(self, formation_id: str):
        super().__init__(
            label="Filter Settings",
            children=[
                "Formation",
                wcc.Dropdown(
                    id=formation_id,
                    clearable=False,
                ),
            ],
        )


class MapSelectorLayout(wcc.Selectors):
    _CM_RANGE = {
        "display": "flex",
        "flexDirection": "row",
    }

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        color_scale_names: List[str],
        property_id: str,
        statistic_id: str,
        colormap_id: str,
        cm_min_id: str,
        cm_max_id: str,
        cm_min_auto_id: str,
        cm_max_auto_id: str,
        visualization_threshold_id: str,
        visualization_update_id: str,
        mass_unit_id: str,
    ):
        default_colormap = (
            "turbo (Seq)"
            if "turbo (Seq)" in color_scale_names
            else color_scale_names[0]
        )
        super().__init__(
            label="Map Settings",
            open_details=True,
            children=[
                html.Div(
                    [
                        "Property",
                        wcc.Dropdown(
                            id=property_id,
                            options=_compile_property_options(),
                            value=MapAttribute.MIGRATION_TIME_SGAS.value,
                            clearable=False,
                        ),
                        "Statistic",
                        wcc.Dropdown(
                            id=statistic_id,
                            options=[s.value for s in SurfaceStatistic],
                            value=SurfaceStatistic.MEAN,
                            clearable=False,
                        ),
                        html.Div(
                            style={
                                "height": "1px",
                                "backgroundColor": "lightgray",
                                "gridColumnStart": "span 2",
                            }
                        ),
                        "Color Scale",
                        dcc.Dropdown(
                            id=colormap_id,
                            options=color_scale_names,
                            value=default_colormap,
                            clearable=False,
                        ),
                        "Minimum",
                        html.Div(
                            [
                                dcc.Input(id=cm_min_id, type="number"),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_min_auto_id,
                                ),
                            ],
                            style=self._CM_RANGE,
                        ),
                        "Maximum",
                        html.Div(
                            [
                                dcc.Input(id=cm_max_id, type="number"),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_max_auto_id,
                                ),
                            ],
                            style=self._CM_RANGE,
                        ),
                        "Visualization threshold",
                        html.Div(
                            [
                                dcc.Input(
                                    id=visualization_threshold_id,
                                    type="number",
                                    value=-1.0,
                                    style={"width": "70%"},
                                ),
                                html.Div(style={"width": "5%"}),
                                html.Button(
                                    "Update",
                                    id=visualization_update_id,
                                    style=LayoutStyle.VISUALIZATION_BUTTON,
                                    n_clicks=0,
                                ),
                            ],
                            style={"display": "flex"},
                        ),
                        "Mass unit (for mass maps)",
                        wcc.Dropdown(
                            id=mass_unit_id,
                            options=["kg", "tons", "M tons"],
                            value="kg",
                            clearable=False,
                        ),
                    ],
                )
            ],
        )


class GraphSelectorsLayout(wcc.Selectors):
    _CM_RANGE = {
        "display": "flex",
        "flexDirection": "row",
    }

    def __init__(
        self,
        graph_source_id: str,
        co2_scale_id: str,
        y_min_ids: List[str],
        y_max_ids: List[str],
        containment_ids: List[str],
        has_zones: bool,
        has_regions: bool,
    ):
        disp_zone = "flex" if has_zones else "none"
        disp_region = "flex" if has_regions else "none"
        header = "Containment for specific"
        if has_zones and not has_regions:
            header += " zone"
        elif has_regions and not has_zones:
            header += " region"
        color_options = [{"label": "Containment (standard)", "value": "containment"}]
        mark_options = [{"label": "Phase", "value": "phase"}]
        if has_zones:
            color_options.append({"label": "Zone", "value": "zone"})
            mark_options.append({"label": "Zone", "value": "zone"})
        if has_regions:
            color_options.append({"label": "Region", "value": "region"})
            mark_options.append({"label": "Region", "value": "region"})
        super().__init__(
            label="Graph Settings",
            open_details=False,
            children=[
                "Source",
                wcc.Dropdown(
                    id=graph_source_id,
                    options=list(GraphSource),
                    value=GraphSource.CONTAINMENT_MASS,
                    clearable=False,
                ),
                "Unit",
                wcc.Dropdown(
                    id=co2_scale_id,
                    options=list(Co2MassScale),
                    value=Co2MassScale.MTONS,
                    clearable=False,
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                "Color by",
                                wcc.Dropdown(
                                    options=color_options,
                                    value="containment",
                                    id=containment_ids[0],
                                    clearable=False,
                                ),
                            ],
                            style={
                                "width": "50%",
                                "flex-direction": "column",
                            },
                        ),
                        html.Div(
                            [
                                "Mark by",
                                wcc.Dropdown(
                                    options=mark_options,
                                    value="phase",
                                    id=containment_ids[1],
                                    clearable=False,
                                ),
                            ],
                            style={
                                "width": "50%",
                                "flex-direction": "column",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",  # disp,
                        "flex-direction": "row",
                        "margin-top": "10px",
                        "margin-bottom": "1px",
                    },
                ),
                html.Div(
                    [
                        "Sort by",
                        dcc.RadioItems(
                            options=["color", "marking"],
                            value="color",
                            id=containment_ids[2],
                            inline=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flex-direction": "row",
                        "margin-top": "5px",
                        "margin-bottom": "1px",
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                "Zone",
                                wcc.Dropdown(
                                    value="all",
                                    id=containment_ids[3],
                                    clearable=False,
                                ),
                            ],
                            id=containment_ids[4],
                            style={
                                "width": "50%" if has_regions else "100%",
                                "display": disp_zone,
                                "flex-direction": "column",
                            },
                        ),
                        html.Div(
                            [
                                "Region",
                                wcc.Dropdown(
                                    value="all",
                                    id=containment_ids[5],
                                    clearable=False,
                                ),
                            ],
                            id=containment_ids[6],
                            style={
                                "width": "50%" if has_zones else "100%",
                                "display": disp_region,
                                "flex-direction": "column",
                            },
                        ),
                        html.Div(
                            [
                                "Phase",
                                wcc.Dropdown(
                                    value="total",
                                    clearable=False,
                                    id=containment_ids[8],
                                ),
                            ],
                            id=containment_ids[9],
                            style={"display": "none"},
                        ),
                        html.Div(
                            [
                                "Containment",
                                wcc.Dropdown(
                                    options=[
                                        {"label": "Total", "value": "total"},
                                        {"label": "Contained", "value": "contained"},
                                        {"label": "Outside", "value": "outside"},
                                        {"label": "Hazardous", "value": "hazardous"},
                                    ],
                                    value="total",
                                    clearable=False,
                                    id=containment_ids[10],
                                ),
                            ],
                            id=containment_ids[11],
                            style={"display": "none"},
                        ),
                    ],
                    id=containment_ids[7],
                    style={"display": "flex"},
                ),
                html.Div(
                    "Fix y-limits in third plot:",
                    style={"margin-top": "10px"},
                ),
                "Minimum",
                html.Div(
                    [
                        dcc.Input(id=y_min_ids[0], type="number"),
                        dcc.Checklist(
                            ["Auto"],
                            ["Auto"],
                            id=y_min_ids[1],
                        ),
                    ],
                    style=self._CM_RANGE,
                ),
                "Maximum",
                html.Div(
                    [
                        dcc.Input(id=y_max_ids[0], type="number"),
                        dcc.Checklist(
                            ["Auto"],
                            ["Auto"],
                            id=y_max_ids[1],
                        ),
                    ],
                    style=self._CM_RANGE,
                ),
            ],
        )


class ExperimentalFeaturesLayout(wcc.Selectors):
    def __init__(self, plume_threshold_id: str, plume_smoothing_id: str):
        super().__init__(
            label="Experimental",
            open_details=False,
            children=[
                html.Div(
                    children=[
                        html.Div("Plume Threshold"),
                        dcc.Input(
                            id=plume_threshold_id,
                            type="number",
                            min=0,
                            value=0.000001,
                            placeholder="Lower property threshold",
                            style={
                                "textAlign": "right",
                            },
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div("Plume Smoothing"),
                        dcc.Input(
                            id=plume_smoothing_id,
                            type="number",
                            min=0,
                            value=0,
                            step=1,
                            placeholder="Smoothing [#pixels]",
                            style={
                                "textAlign": "right",
                            },
                        ),
                    ],
                ),
            ],
        )


class EnsembleSelectorLayout(wcc.Selectors):
    def __init__(self, ensemble_id: str, realization_id: str, ensembles: List[str]):
        super().__init__(
            label="Ensemble",
            open_details=True,
            children=[
                "Ensemble",
                wcc.Dropdown(
                    id=ensemble_id,
                    options=[{"value": en, "label": en} for en in ensembles],
                    value=ensembles[0],
                    clearable=False,
                ),
                "Realization",
                wcc.SelectWithLabel(
                    id=realization_id,
                    value=[],
                    multi=True,
                ),
            ],
        )


def _compile_property_options() -> List[Dict[str, Any]]:
    return [
        {
            "label": html.Span(["SGAS:"], style={"text-decoration": "underline"}),
            "value": "",
            "disabled": True,
        },
        {
            "label": MapAttribute.MIGRATION_TIME_SGAS.value,
            "value": MapAttribute.MIGRATION_TIME_SGAS.value,
        },
        {"label": MapAttribute.MAX_SGAS.value, "value": MapAttribute.MAX_SGAS.value},
        {
            "label": MapAttribute.SGAS_PLUME.value,
            "value": MapAttribute.SGAS_PLUME.value,
        },
        {
            "label": html.Span(["AMFG:"], style={"text-decoration": "underline"}),
            "value": "",
            "disabled": True,
        },
        {
            "label": MapAttribute.MIGRATION_TIME_AMFG.value,
            "value": MapAttribute.MIGRATION_TIME_AMFG.value,
        },
        {"label": MapAttribute.MAX_AMFG.value, "value": MapAttribute.MAX_AMFG.value},
        {
            "label": MapAttribute.AMFG_PLUME.value,
            "value": MapAttribute.AMFG_PLUME.value,
        },
        {
            "label": html.Span(["MASS:"], style={"text-decoration": "underline"}),
            "value": "",
            "disabled": True,
        },
        {"label": MapAttribute.MASS.value, "value": MapAttribute.MASS.value},
        {"label": MapAttribute.DISSOLVED.value, "value": MapAttribute.DISSOLVED.value},
        {"label": MapAttribute.FREE.value, "value": MapAttribute.FREE.value},
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
                    """If you have any feedback regarding the CO2-Leakage application,
                    don't hesitate to"""
                ),
                dcc.Link(
                    ["send an email!"],
                    href=f"mailto:{get_emails()}&subject=Feedback regarding the "
                    f"CO2-Leakage application",
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
    decrypted_email = []
    for char in encrypted_email:
        decrypted_email.append(chr(ord(char) ^ key))
    return "".join(decrypted_email)


def get_emails() -> str:
    emails = [
        decrypt_email(m, i + 1)
        for i, m in enumerate(
            [
                "GLLNAdpthons/bnl",
                "OLCIKBgswklmp,amo",
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
) -> List[Dict[str, str]]:
    zone = {"display": "none", "flex-direction": "column", "width": "100%"}
    region = {"display": "none", "flex-direction": "column", "width": "100%"}
    phase = {"display": "none", "flex-direction": "column", "width": "100%"}
    containment = {"display": "none", "flex-direction": "column", "width": "100%"}
    if color_choice == "containment":
        if mark_choice == "phase":
            zone["width"] = "50%" if has_regions else "100%"
            zone["display"] = "flex" if has_zones else "none"
            region["width"] = "50%" if has_zones else "100%"
            region["display"] = "flex" if has_regions else "none"
        elif mark_choice == "none":
            zone["width"] = "33%" if has_regions else "50%"
            zone["display"] = "flex" if has_zones else "none"
            region["width"] = "33%" if has_zones else "50%"
            region["display"] = "flex" if has_regions else "none"
            phase["width"] = (
                "33%"
                if has_zones and has_regions
                else "100%"
                if not has_regions and not has_zones
                else "50%"
            )
            phase["display"] = "flex"
        else:  # mark_choice == "zone" / "region"
            phase["display"] = "flex"
    else:  # color_choice == "zone" / "region"
        if mark_choice == "phase":
            containment["display"] = "flex"
        elif mark_choice == "none":
            containment["width"] = "50%"
            containment["display"] = "flex"
            phase["width"] = "50%"
            phase["display"] = "flex"
        else:  # mark == "containment"
            phase["display"] = "flex"
    return [zone, region, phase, containment]
