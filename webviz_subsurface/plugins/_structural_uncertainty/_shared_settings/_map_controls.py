from typing import Dict, List, Optional, Tuple

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, State, callback, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds
from ._dialog import clear_all_apply_dialog_buttons, dialog_layout, open_dialog_layout


class MapControls(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        # -surface A
        SURFACE_ATTRIBUTE_A = "surface-attribute-a"
        SURFACE_NAME_A = "surface-name-a"
        CALCULATION_REAL_A = "calculation-real-a"
        CALCULATE_WELL_INTER_A = "calculate-well-inter-a"
        ENSEMBLE_A = "ensemble-a"

        # -surface B
        SURFACE_ATTRIBUTE_B = "surface-attribute-b"
        SURFACE_NAME_B = "surface-name-b"
        CALCULATION_REAL_B = "calculation-real-b"
        CALCULATE_WELL_INTER_B = "calculate-well-inter-b"
        ENSEMBLE_B = "ensemble-b"

        # -settings
        AUTO_COMP_DIFF = "auto-comp-diff"
        COLOR_RANGES = "color-ranges"
        SURFACE_A_MIN = "surface-a-min"
        SURFACE_B_MIN = "surface-b-min"
        SURFACE_A_MAX = "surface-a-max"
        SURFACE_B_MAX = "surface-b-max"
        SYNC_RANGE_ON_MAPS = "sync-range-on-maps"

        # -filter
        REAL_FILTER = "real-filter"
        SELECTED_REAL = "selected-real"

    def __init__(
        self,
        surface_attributes: List[str],
        surface_names: List[str],
        ensembles: List[str],
        realizations: List[int],
        use_wells: bool,
        initial_settings: Dict,
    ) -> None:
        super().__init__("Map Controls")

        self.surface_attributes = surface_attributes
        self.surface_names = surface_names
        self.ensembles = ensembles
        self.realizations = realizations
        self.use_wells = use_wells
        self.initial_settings = initial_settings

    def layout(self) -> List[Component]:
        return [
            # Surface A
            wcc.Selectors(
                label="Surface A",
                children=[
                    wcc.Dropdown(
                        label="Surface attribute",
                        id=self.register_component_unique_id(
                            MapControls.Ids.SURFACE_ATTRIBUTE_A
                        ),
                        options=[
                            {"label": val, "value": val}
                            for val in self.surface_attributes
                        ],
                        value=self.surface_attributes[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Surface name",
                        id=self.register_component_unique_id(
                            MapControls.Ids.SURFACE_NAME_A
                        ),
                        options=[
                            {"label": val, "value": val} for val in self.surface_names
                        ],
                        value=self.surface_names[0],
                        clearable=False,
                    ),
                    html.Div(
                        style={
                            "display": ("inline" if len(self.ensembles) > 1 else "none")
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble",
                                id=self.register_component_unique_id(
                                    MapControls.Ids.ENSEMBLE_A
                                ),
                                options=[
                                    {"label": val, "value": val}
                                    for val in self.ensembles
                                ],
                                value=self.ensembles[0],
                                clearable=False,
                            ),
                        ],
                    ),
                    wcc.Dropdown(
                        label="Calculation/Realization",
                        id=self.register_component_unique_id(
                            MapControls.Ids.CALCULATION_REAL_A
                        ),
                        options=[
                            {"label": val, "value": val}
                            for val in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]
                            + [str(real) for real in self.realizations]
                        ],
                        value=str(self.realizations[0]),
                        clearable=False,
                    ),
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            MapControls.Ids.CALCULATE_WELL_INTER_A
                        ),
                        options=[
                            {
                                "label": "Calculate well intersections",
                                "value": "intersect_well",
                            }
                        ]
                        if self.use_wells
                        else [],
                        value=[],
                    ),
                ],
            ),
            # Surface B
            wcc.Selectors(
                label="Surface B",
                children=[
                    wcc.Dropdown(
                        label="Surface attribute",
                        id=self.register_component_unique_id(
                            MapControls.Ids.SURFACE_ATTRIBUTE_B
                        ),
                        options=[
                            {"label": val, "value": val}
                            for val in self.surface_attributes
                        ],
                        value=self.surface_attributes[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Surface name",
                        id=self.register_component_unique_id(
                            MapControls.Ids.SURFACE_NAME_B
                        ),
                        options=[
                            {"label": val, "value": val} for val in self.surface_names
                        ],
                        value=self.surface_names[0],
                        clearable=False,
                    ),
                    html.Div(
                        style={
                            "display": ("inline" if len(self.ensembles) > 1 else "none")
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble",
                                id=self.register_component_unique_id(
                                    MapControls.Ids.ENSEMBLE_B
                                ),
                                options=[
                                    {"label": val, "value": val}
                                    for val in self.ensembles
                                ],
                                value=self.ensembles[0],
                                clearable=False,
                            ),
                        ],
                    ),
                    wcc.Dropdown(
                        label="Calculation/Realization",
                        id=self.register_component_unique_id(
                            MapControls.Ids.CALCULATION_REAL_B
                        ),
                        options=[
                            {"label": val, "value": val}
                            for val in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]
                            + [str(real) for real in self.realizations]
                        ],
                        value=str(self.realizations[0]),
                        clearable=False,
                    ),
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            MapControls.Ids.CALCULATE_WELL_INTER_B
                        ),
                        options=[
                            {
                                "label": "Calculate well intersections",
                                "value": "intersect_well",
                            }
                        ]
                        if self.use_wells
                        else [],
                        value=[],
                    ),
                ],
            ),
            # Settings
            wcc.Selectors(
                open_details=False,
                label="⚙️ Settings",
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            MapControls.Ids.AUTO_COMP_DIFF
                        ),
                        options=[
                            {
                                "label": "Auto compute difference map",
                                "value": "compute_diffmap",
                            }
                        ],
                        value=["compute_diffmap"],
                    ),
                    html.Div(
                        children=[
                            wcc.Label(
                                "Color ranges:",
                                style={"font-weight": "bold"},
                            ),
                            wcc.FlexBox(
                                style={"display": "flex", "align-items": "center"},
                                children=[
                                    wcc.Label(
                                        "Surface A",
                                        style={"flex": 1, "minWidth": "40px"},
                                    ),
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            MapControls.Ids.SURFACE_A_MIN
                                        ),
                                        style={"flex": 1, "minWidth": "40px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Min",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            MapControls.Ids.SURFACE_A_MAX
                                        ),
                                        style={"flex": 1, "minWidth": "40px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Max",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                            ),
                            wcc.FlexBox(
                                style={"display": "flex", "align-items": "center"},
                                children=[
                                    wcc.Label(
                                        "Surface B",
                                        style={"flex": 1, "minWidth": "40px"},
                                    ),
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            MapControls.Ids.SURFACE_B_MIN
                                        ),
                                        style={"flex": 1, "minWidth": "40px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Min",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            MapControls.Ids.SURFACE_B_MAX
                                        ),
                                        style={"flex": 1, "minWidth": "40px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Max",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                            ),
                            wcc.Checklist(
                                id=self.register_component_unique_id(
                                    MapControls.Ids.SYNC_RANGE_ON_MAPS
                                ),
                                options=[
                                    {
                                        "label": "Sync range on maps",
                                        "value": "sync_range",
                                    }
                                ],
                                value=[],
                            ),
                        ],
                    ),
                ],
            ),
            wcc.Selectors(
                label="Filters",
                children=[
                    html.Div(
                        children=[
                        open_dialog_layout(
                            uuid=self.register_component_unique_id(
                                MapControls.Ids.REAL_FILTER
                            ),
                            dialog_id="realization-filter",
                            title="Realization filter",
                        ),]
                    ),
                ],
            ),
           dialog_layout(
                    uuid=self.component_unique_id(MapControls.Ids.REAL_FILTER).to_string(),
                    dialog_id="realization-filter",
                    title="Filter realizations",
                    children=[
                        html.Div(
                            style={"marginTop": "10px"},
                            children=html.Label(
                                children=[
                                    wcc.Select(
                                        id=self.register_component_unique_id(MapControls.Ids.SELECTED_REAL),
                                        options=[{"label": real, "value": real} for real in self.realizations],
                                        value=[str(val) for val in self.initial_settings.get(
                                                                "intersection_data", {}
                                                            ).get("realizations", self.realizations)],
                                        multi=True,
                                        size=20,
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ]
                            ),
                        ),
                        clear_all_apply_dialog_buttons(
                            uuid=self.component_unique_id(MapControls.Ids.REAL_FILTER).to_string(), dialog_id="realization-filter"
                        ),
                    ],
                ), 
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTRIBUTE_A), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.SURFACE_ATTRIBUTE_A
                ).to_string(),
                "value",
            ),
        )
        def _set_surf_attr_a(surf_a: str) -> str:
            return surf_a

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_NAME_A), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_NAME_A).to_string(),
                "value",
            ),
        )
        def _set_surf_name_a(surf_a: str) -> str:
            return surf_a

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.CALCULATION_REAL_A), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.CALCULATION_REAL_A
                ).to_string(),
                "value",
            ),
        )
        def _set_calc_real_a(real_a: str) -> str:
            return real_a

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.CALCULATE_WELL_INTER_A),
                "data",
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.CALCULATE_WELL_INTER_A
                ).to_string(),
                "value",
            ),
        )
        def _set_well_inter_a(well_a: List[str]) -> List[str]:
            return well_a

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTRIBUTE_B), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.SURFACE_ATTRIBUTE_B
                ).to_string(),
                "value",
            ),
        )
        def _set_surf_attr_b(surf_b: str) -> str:
            return surf_b

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_NAME_B), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_NAME_B).to_string(),
                "value",
            ),
        )
        def _set_surf_name_b(surf_b: str) -> str:
            return surf_b

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.CALCULATION_REAL_B), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.CALCULATION_REAL_B
                ).to_string(),
                "value",
            ),
        )
        def _set_calc_real_b(real_b: str) -> str:
            return real_b

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.CALCULATE_WELL_INTER_B),
                "data",
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.CALCULATE_WELL_INTER_B
                ).to_string(),
                "value",
            ),
        )
        def _set_well_inter_b(well_b: List[str]) -> List[str]:
            return well_b

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.AUTO_COMP_DIFF), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.AUTO_COMP_DIFF).to_string(),
                "value",
            ),
        )
        def _set_auto_diff(auto: List[str]) -> List[str]:
            return auto

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_A_MIN), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_A_MIN).to_string(),
                "value",
            ),
        )
        def _set_surf_a_min(min_a: int) -> int:
            return min_a

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_A_MAX), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_A_MAX).to_string(),
                "value",
            ),
        )
        def _set_surf_a_max(max_a: int) -> int:
            return max_a

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MIN), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_B_MIN).to_string(),
                "value",
            ),
        )
        def _set_surf_b_min(min_b: int) -> int:
            return min_b

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_B_MAX), "data"),
            Input(
                self.component_unique_id(MapControls.Ids.SURFACE_B_MAX).to_string(),
                "value",
            ),
        )
        def _set_surf_b_max(max_b: int) -> int:
            return max_b

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SYNC_RANGE_ON_MAPS), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.SYNC_RANGE_ON_MAPS
                ).to_string(),
                "value",
            ),
        )
        def _set_sync(sync: List[str]) -> List[str]:
            return sync
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLE_A), "data"
            ),
            Output(
                self.get_store_unique_id(PluginIds.Stores.ENSEMBLE_B), "data"
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.ENSEMBLE_A
                ).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.ENSEMBLE_B
                ).to_string(),
                "value",
            ),
        )
        def _set_ensembles(ens_a: str, ens_b: str) -> Tuple[str, str]:
            return [ens_a, ens_b]
        @callback(
            #add layout to realization button first
            Output(
                {
                    "id": self.component_unique_id(
                    MapControls.Ids.REAL_FILTER
                ).to_string(),
                    "dialog_id": "realization-filter",
                    "element": "apply",
                },
                "disabled",
            ),
            Output(
                {
                    "id": self.component_unique_id(
                    MapControls.Ids.REAL_FILTER
                ).to_string(),
                    "dialog_id": "realization-filter",
                    "element": "apply",
                },
                "style",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.REAL_STORE),
                "data",
            ),
            Input(
                self.component_unique_id(
                    MapControls.Ids.SELECTED_REAL
                ).to_string(),
                "value",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.INITIAL_REALS),
                "data",)
        )
        def _activate_realization_apply_btn(
            stored_reals: List, selected_reals: List, initial_reals: List
        ) -> Tuple[bool, Dict[str, str]]:
            if stored_reals == None:
                stored_reals = initial_reals
            if stored_reals is None or selected_reals is None:
                raise PreventUpdate
            if set(stored_reals) == set(selected_reals):
                return True, {"visibility": "hidden"}
            return False, {"visibility": "visible"}
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.REAL_STORE),
                "data",
            ),
            Input(
                {
                    "id": self.component_unique_id(
                    MapControls.Ids.REAL_FILTER
                ).to_string(),
                    "dialog_id": "realization-filter",
                    "element": "apply",
                },
                "n_clicks",
            ),
            State(
                self.component_unique_id(
                    MapControls.Ids.SELECTED_REAL
                ).to_string(),
                "value",
            ),
            prevent_initial_call = True
        )
        def _store_realizations(btn_click: Optional[int], selected_reals: List) -> List:
            if btn_click:
                return selected_reals
            raise PreventUpdate
