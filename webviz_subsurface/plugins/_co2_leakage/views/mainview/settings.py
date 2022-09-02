from typing import List, Dict

import dash
import webviz_core_components as wcc
from dash import html, dcc, callback, Output, Input, State
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_surface_provider.ensemble_surface_provider import \
    SurfaceStatistic, EnsembleSurfaceProvider
from webviz_subsurface.plugins._co2_leakage._utilities.callbacks import property_origin
from webviz_subsurface.plugins._co2_leakage._utilities.formation_alias import \
    surface_name_aliases
from webviz_subsurface.plugins._co2_leakage._utilities.general import MapAttribute, \
    fmu_realization_paths
from webviz_subsurface.plugins._map_viewer_fmu.color_tables import default_color_tables


class ViewSettings(SettingsGroupABC):
    class Ids:
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
        map_attribute_names: Dict[MapAttribute, str],
    ):
        super().__init__("Settings")
        self._ensemble_paths = ensemble_paths
        self._ensemble_surface_providers = ensemble_surface_providers
        self._map_attribute_names = map_attribute_names

    def layout(self):
        return [
            EnsembleSelectorLayout(
                self.register_component_unique_id(self.Ids.ENSEMBLE),
                self.register_component_unique_id(self.Ids.REALIZATION),
                list(self._ensemble_paths.keys()),
            ),
            FilterSelectorLayout(
                self.register_component_unique_id(self.Ids.FORMATION)
            ),
            MapSelectorLayout(
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
            Output(self.component_unique_id(self.Ids.REALIZATION).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
        )
        def set_realizations(ensemble):
            rz_paths = fmu_realization_paths(self._ensemble_paths[ensemble])
            realizations = [
                dict(label=r, value=r)
                for r in sorted(rz_paths.keys())
            ]
            return realizations, [realizations[0]["value"]]

        @callback(
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), 'options'),
            Output(self.component_unique_id(self.Ids.FORMATION).to_string(), 'value'),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), 'value'),
            State(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), 'value'),
            State(self.component_unique_id(self.Ids.FORMATION).to_string(), 'value'),
        )
        def set_formations(prop, ensemble, current_value):
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
            Output(self.component_unique_id(self.Ids.STATISTIC).to_string(), "disabled"),
            Input(self.component_unique_id(self.Ids.REALIZATION).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.PROPERTY).to_string(), "value"),
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
            Output(self.component_unique_id(self.Ids.CM_MIN).to_string(), "disabled"),
            Output(self.component_unique_id(self.Ids.CM_MAX).to_string(), "disabled"),
            Input(self.component_unique_id(self.Ids.CM_MIN_AUTO).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.CM_MAX_AUTO).to_string(), "value"),
        )
        def set_color_range_data(min_auto, max_auto):
            return len(min_auto) == 1, len(max_auto) == 1


class FilterSelectorLayout(wcc.Selectors):
    def __init__(self, formation_id):
        super().__init__(
            label="Filter Settings",
            children=[
                "Formation",
                wcc.Dropdown(
                    id=formation_id,
                ),
            ]
        )


class MapSelectorLayout(wcc.Selectors):
    class Style:
        CM_RANGE = {
            "display": "flex",
            "flexDirection": "row",
        }

    def __init__(
        self,
        property_id,
        statistic_id,
        colormap_id,
        cm_min_id,
        cm_max_id,
        cm_min_auto_id,
        cm_max_auto_id,
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
                            options=[d["name"] for d in _color_tables()],
                            value=_color_tables()[0]["name"],
                        ),
                        "Minimum",
                        html.Div(
                            [
                                dcc.Input(
                                    id=cm_min_id,
                                    type="number"
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_min_auto_id,
                                ),
                            ],
                            style=self.Style.CM_RANGE,
                        ),
                        "Maximum",
                        html.Div(
                            [
                                dcc.Input(
                                    id=cm_max_id,
                                    type="number"
                                ),
                                dcc.Checklist(
                                    ["Auto"],
                                    ["Auto"],
                                    id=cm_max_auto_id,
                                ),
                            ],
                            style=self.Style.CM_RANGE,
                        ),
                    ],
                )
            ],
        )


class ExperimentalFeaturesLayout(wcc.Selectors):
    def __init__(self, plume_threshold_id, plume_smoothing_id):
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
            ]
        )


class EnsembleSelectorLayout(wcc.Selectors):
    def __init__(self, ensemble_id, realization_id, ensembles: List[str]):
        super().__init__(
            label="Ensemble",
            open_details=True,
            children=[
                "Ensemble",
                wcc.Dropdown(
                    id=ensemble_id,
                    options=[
                        dict(value=en, label=en)
                        for en in ensembles
                    ],
                    value=ensembles[0],
                    clearable=False,
                ),
                "Realization",
                wcc.Dropdown(
                    id=realization_id,
                    value=[],
                    multi=True,
                ),
            ]
        )


def _compile_property_options():
    return [
        {"label": "SGAS", "value": "", "disabled": True},
        {"label": MapAttribute.MIGRATION_TIME.value, "value": MapAttribute.MIGRATION_TIME.value},
        {"label": MapAttribute.MAX_SGAS.value, "value": MapAttribute.MAX_SGAS.value},
        {"label": MapAttribute.SGAS_PLUME.value, "value": MapAttribute.SGAS_PLUME.value},
        {"label": "AMFG", "value": "", "disabled": True},
        {"label": MapAttribute.MAX_AMFG.value, "value": MapAttribute.MAX_AMFG.value},
        {"label": MapAttribute.AMFG_PLUME.value, "value": MapAttribute.AMFG_PLUME.value},
    ]


def _color_tables():
    # Source: https://waldyrious.net/viridis-palette-generator/ + matplotlib._cm_listed
    return default_color_tables + [
        {
            "name": "Viridis",
            "discrete": False,
            "colors": [
                [0.0, 253, 231, 37],
                [0.25, 94, 201, 98],
                [0.50, 33, 145, 140],
                [0.75, 59, 82, 139],
                [1.0, 68, 1, 84],
            ],
        },
        {
            "name": "Inferno",
            "discrete": False,
            "colors": [
                [0.0, 252, 255, 164],
                [0.25, 249, 142, 9],
                [0.5, 188, 55, 84],
                [0.75, 87, 16, 110],
                [1.0, 0, 0, 4],
            ],
        },
        {
            "name": "Magma",
            "discrete": False,
            "colors": [
                [0.0, 252, 253, 191],
                [0.25, 252, 137, 97],
                [0.5, 183, 55, 121],
                [0.75, 81, 18, 124],
                [1.0, 0, 0, 4],
            ],
        },
        {
            "name": "Plasma",
            "discrete": False,
            "colors": [
                [0.0, 240, 249, 33],
                [0.25, 248, 149, 64],
                [0.5, 204, 71, 120],
                [0.75, 126, 3, 168],
                [1.0, 13, 8, 135],
            ],
        },
        {
            "name": "Cividis",
            "discrete": False,
            "colors": [
                 [0.0, 0, 32, 77],
                 [0.25, 64, 77, 107],
                 [0.5, 124, 123, 120],
                 [0.75, 188, 175, 111],
                 [1.0, 255, 234, 70],
            ],
        },
    ]
