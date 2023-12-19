from typing import Any, Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
from dash import Input, Output, State, callback, dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers import EnsembleTableProvider
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
    ZoneViews,
)


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        OPTIONS_DIALOG_BUTTON = "options-dialog-button"
        OPTIONS_DIALOG = "options-dialog"
        OPTIONS_DIALOG_OPTIONS = "options-dialog-options"
        OPTIONS_DIALOG_WELL_FILTER = "options-dialog-well-filter"

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
        ZONE = "zone"
        ZONE_VIEW = "zone_view"

        PLUME_THRESHOLD = "plume-threshold"
        PLUME_SMOOTHING = "plume-smoothing"

        VISUALIZATION_THRESHOLD = "visualization-threshold"
        VISUALIZATION_SHOW_0 = "visualization-show-0"

        FEEDBACK_BUTTON = "feedback-button"
        FEEDBACK = "feedback"

    def __init__(
        self,
        ensemble_paths: Dict[str, str],
        ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
        initial_surface: Optional[str],
        map_attribute_names: Dict[MapAttribute, str],
        color_scale_names: List[str],
        well_names: List[str],
        zone_options: Dict[str, Dict[str, List[str]]],
    ):
        super().__init__("Settings")
        self._ensemble_paths = ensemble_paths
        self._ensemble_surface_providers = ensemble_surface_providers
        self._map_attribute_names = map_attribute_names
        self._color_scale_names = color_scale_names
        self._initial_surface = initial_surface
        self._well_names = well_names
        self._zone_options = zone_options
        self._has_zones = max(
            [len(zn) > 0 for ens, zd in zone_options.items() for zn in zd.values()]
        )

    def layout(self) -> List[Component]:
        return [
            DialogLayout(self._well_names),
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
                self.register_component_unique_id(self.Ids.VISUALIZATION_SHOW_0),
            ),
            GraphSelectorsLayout(
                self.register_component_unique_id(self.Ids.GRAPH_SOURCE),
                self.register_component_unique_id(self.Ids.CO2_SCALE),
                self.register_component_unique_id(self.Ids.Y_MIN_GRAPH),
                self.register_component_unique_id(self.Ids.Y_MAX_GRAPH),
                self.register_component_unique_id(self.Ids.Y_MIN_AUTO_GRAPH),
                self.register_component_unique_id(self.Ids.Y_MAX_AUTO_GRAPH),
                self.register_component_unique_id(self.Ids.ZONE),
                self.register_component_unique_id(self.Ids.ZONE_VIEW),
                self._has_zones,
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
            # Formation names
            formations = [{"label": v.title(), "value": v} for v in surfaces]
            picked_formation = None
            if len(formations) != 0:
                if current_value is None and self._initial_surface in surfaces:
                    picked_formation = self._initial_surface
                elif current_value in surfaces:
                    picked_formation = dash.no_update
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
            Input(
                self.component_unique_id(self.Ids.VISUALIZATION_SHOW_0).to_string(),
                "value",
            ),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
        )
        def set_visualization_threshold(show_0: List[str], attribute: str) -> bool:
            return (
                len(show_0) == 1
                or MapAttribute(attribute) == MapAttribute.MIGRATION_TIME
            )

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
        ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
            if ensemble is not None:
                zones = self._zone_options[ensemble][source]
                if len(zones) > 0:
                    return zones, dash.no_update if current_value in zones else "all"
            return [], None

        @callback(
            Output(self.component_unique_id(self.Ids.ZONE).to_string(), "disabled"),
            Input(self.component_unique_id(self.Ids.ZONE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.ZONE_VIEW).to_string(), "value"),
        )
        def disable_zone(zone: str, zone_view: str) -> bool:
            return zone is None or zone_view == ZoneViews.ZONESPLIT


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
        well_names: List[str],
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
                            style={
                                "flex": 3,
                                "minWidth": "20px",
                                "display": "block" if well_names else "none",
                            },
                            children=WellFilter(well_names),
                        ),
                    ],
                    style={"width": "20vw"},
                ),
            ],
        )


class WellFilter(html.Div):
    def __init__(self, well_names: List[str]) -> None:
        super().__init__(
            style={"display": "block" if well_names else "none"},
            children=wcc.SelectWithLabel(
                label=LayoutLabels.WELL_FILTER,
                id=ViewSettings.Ids.OPTIONS_DIALOG_WELL_FILTER,
                options=[{"label": i, "value": i} for i in well_names],
                value=well_names,
                size=min(20, len(well_names)),
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
        visualization_show_0_id: str,
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
                            value=MapAttribute.MIGRATION_TIME.value,
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
                                dcc.Input(id=visualization_threshold_id, type="number"),
                                dcc.Checklist(
                                    ["Show 0"],
                                    ["Show 0"],
                                    id=visualization_show_0_id,
                                ),
                            ],
                            style=self._CM_RANGE,
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
        y_min_id: str,
        y_max_id: str,
        y_min_auto_id: str,
        y_max_auto_id: str,
        zone_id: str,
        zone_view_id: str,
        has_zones: bool,
    ):
        disp = "flex" if has_zones else "none"
        super().__init__(
            label="Graph Settings",
            open_details=False,
            children=[
                html.Div(
                    [
                        dcc.RadioItems(
                            [ZoneViews.CONTAINMENTSPLIT, ZoneViews.ZONESPLIT],
                            ZoneViews.CONTAINMENTSPLIT,
                            id=zone_view_id,
                        ),
                    ],
                    style={"display": disp, "flex-direction": "column"},
                ),
                "Source",
                wcc.Dropdown(
                    id=graph_source_id,
                    options=list(GraphSource),
                    value=GraphSource.CONTAINMENT_MASS,
                    clearable=False,
                ),
                html.Div(
                    [
                        "Containment plot for specific zone",
                        wcc.Dropdown(
                            id=zone_id,
                            clearable=False,
                        ),
                    ],
                    style={"display": disp, "flex-direction": "column"},
                ),
                "Unit",
                wcc.Dropdown(
                    id=co2_scale_id,
                    options=list(Co2MassScale),
                    value=Co2MassScale.MTONS,
                    clearable=False,
                ),
                "Minimum",
                html.Div(
                    [
                        dcc.Input(id=y_min_id, type="number"),
                        dcc.Checklist(
                            ["Auto"],
                            ["Auto"],
                            id=y_min_auto_id,
                        ),
                    ],
                    style=self._CM_RANGE,
                ),
                "Maximum",
                html.Div(
                    [
                        dcc.Input(id=y_max_id, type="number"),
                        dcc.Checklist(
                            ["Auto"],
                            ["Auto"],
                            id=y_max_auto_id,
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
            "label": MapAttribute.MIGRATION_TIME.value,
            "value": MapAttribute.MIGRATION_TIME.value,
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
    """Layout for the options dialog"""

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
                    """If you have any feedback regarding the CO2-leakage application,  
                please contact XXX@XX.X."""
                )
            ],
        )


class FeedbackButton(html.Button):
    def __init__(self) -> None:
        style = LayoutStyle.OPTIONS_BUTTON
        style["display"] = "none"
        super().__init__(
            LayoutLabels.FEEDBACK,
            id=ViewSettings.Ids.FEEDBACK_BUTTON,
            style=style,
            n_clicks=0,
        )
