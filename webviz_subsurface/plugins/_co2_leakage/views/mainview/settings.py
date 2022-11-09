from typing import Any, Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
from dash import Input, Output, State, callback, dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import (
    EnsembleSurfaceProvider,
    SurfaceStatistic,
)
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import property_origin
from webviz_subsurface.plugins._co2_leakage._utilities.generic import MapAttribute


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
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

        PLUME_THRESHOLD = "plume-threshold"
        PLUME_SMOOTHING = "plume-smoothing"

    def __init__(
        self,
        ensemble_paths: Dict[str, str],
        ensemble_surface_providers: Dict[str, EnsembleSurfaceProvider],
        initial_surface: Optional[str],
        map_attribute_names: Dict[MapAttribute, str],
        color_scale_names: List[str],
    ):
        super().__init__("Settings")
        self._ensemble_paths = ensemble_paths
        self._ensemble_surface_providers = ensemble_surface_providers
        self._map_attribute_names = map_attribute_names
        self._color_scale_names = color_scale_names
        self._initial_surface = initial_surface

    def layout(self) -> List[Component]:
        return [
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
            ),
            ExperimentalFeaturesLayout(
                self.register_component_unique_id(self.Ids.PLUME_THRESHOLD),
                self.register_component_unique_id(self.Ids.PLUME_SMOOTHING),
            ),
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
                    picked_formation = formations[0]["value"]
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
    ):
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
                            value=color_scale_names[0],
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
                    ],
                )
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
                    options=[dict(value=en, label=en) for en in ensembles],
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
        {"label": "SGAS", "value": "", "disabled": True},
        {
            "label": MapAttribute.MIGRATION_TIME.value,
            "value": MapAttribute.MIGRATION_TIME.value,
        },
        {"label": MapAttribute.MAX_SGAS.value, "value": MapAttribute.MAX_SGAS.value},
        {
            "label": MapAttribute.SGAS_PLUME.value,
            "value": MapAttribute.SGAS_PLUME.value,
        },
        {"label": "AMFG", "value": "", "disabled": True},
        {"label": MapAttribute.MAX_AMFG.value, "value": MapAttribute.MAX_AMFG.value},
        {
            "label": MapAttribute.AMFG_PLUME.value,
            "value": MapAttribute.AMFG_PLUME.value,
        },
    ]
