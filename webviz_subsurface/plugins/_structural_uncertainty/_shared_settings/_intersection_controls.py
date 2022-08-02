import json
from typing import Callable, Dict, List, Optional, Tuple, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback, callback_context, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from pyparsing import line
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._components import ColorPicker

from .._plugin_ids import PluginIds


class IntersectionControls(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        # intersection controls
        SOURCE = "source"
        X_LINE_BOX = "x-line-box"
        X_LINE = "x-line"
        Y_LINE_BOX = "y-line-box"
        Y_LINE = "y-line"
        STEP_X = "step-x"
        STEP_Y = "step-y"
        WELL_BOX = "well-box"
        WELL = "well"
        SURFACE_ATTR = "surface-attr"
        SURFACE_NAMES = "surface-names"
        SHOW_SURFACES = "show-surfaces"
        UPDATE_INTERSECTION = "update-intersection"
        UNCERTAINTY_TABLE = "uncertainty-table"
        ENSEMBLES = "ensembles"

        # -settings
        RESOLUTION = "resolution"
        EXTENSION = "extension"
        DEPTH_RANGE = "depth-range"
        Z_RANGE_MIN = "z-range-min"
        Z_RANGE_MAX = "z-range-max"
        TRUNKATE_LOCK = "trunkate-lock"
        KEEP_ZOOM = "keep-zoom"
        INTERSECTION_COLORS = "intersection-colors"

    def __init__(
        self,
        surface_attributes: List[str],
        surface_names: List[str],
        ensembles: List[str],
        use_wells: bool,
        well_names: List[str],
        surface_geometry: Dict,
        initial_settings: Dict,
        realizations: List[Union[str, int]],
        color_picker: ColorPicker,
    ) -> None:
        super().__init__("Intersection Controls")

        self.surface_attributes = surface_attributes
        self.surface_names = surface_names
        self.ensembles = ensembles
        self.use_wells = use_wells
        self.well_names = well_names
        self.surface_geometry = surface_geometry
        self.initial_settings = initial_settings
        self.realizations = realizations
        self.color_picker = color_picker
        self.source_opt = [
                    {"label": "Intersect polyline from Surface A", "value": "polyline"},
                    {"label": "Intersect x-line from Surface A", "value": "xline"},
                    {"label": "Intersect y-line from Surface A", "value": "yline"},
                ]
        if use_wells:
                    self.source_opt.append({"label": "Intersect well", "value": "well"})

    def layout(self) -> List[Component]:
        return [
            # Source
            wcc.Dropdown(
                label="Intersection source",
                id=self.register_component_unique_id(IntersectionControls.Ids.SOURCE),
                options=self.source_opt,
                value="well" if self.use_wells else "polyline",
                clearable=False,
            ),
            # X-line
            html.Div(
                style={
                    "display": "none",
                },
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.X_LINE_BOX
                ),
                children=[
                    html.Label("X-Line:"),
                    wcc.FlexBox(
                        style={"fontSize": "0.8em"},
                        children=[
                            dcc.Input(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.X_LINE
                                ),
                                style={"flex": 3, "minWidth": "100px"},
                                type="number",
                                value=round(self.surface_geometry["xmin"]),
                                min=round(self.surface_geometry["xmin"]),
                                max=round(self.surface_geometry["xmax"]),
                                step=500,
                                persistence=True,
                                persistence_type="session",
                            ),
                            wcc.Label(
                                style={
                                    "flex": 1,
                                    "marginLeft": "10px",
                                    "minWidth": "20px",
                                },
                                children="Step:",
                            ),
                            dcc.Input(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.STEP_X
                                ),
                                style={"flex": 2, "minWidth": "20px"},
                                value=500,
                                type="number",
                                min=1,
                                max=round(self.surface_geometry["xmax"])
                                - round(self.surface_geometry["xmin"]),
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ],
            ),
            # Y-line
            html.Div(
                style={
                    "display": "none",
                },
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.Y_LINE_BOX
                ),
                children=[
                    html.Label("Y-Line:"),
                    wcc.FlexBox(
                        style={"fontSize": "0.8em"},
                        children=[
                            dcc.Input(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.Y_LINE
                                ),
                                style={"flex": 3, "minWidth": "100px"},
                                type="number",
                                value=round(self.surface_geometry["ymin"]),
                                min=round(self.surface_geometry["ymin"]),
                                max=round(self.surface_geometry["ymax"]),
                                step=50,
                                persistence=True,
                                persistence_type="session",
                            ),
                            wcc.Label(
                                style={
                                    "flex": 1,
                                    "marginLeft": "10px",
                                    "minWidth": "20px",
                                },
                                children="Step:",
                            ),
                            dcc.Input(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.STEP_Y
                                ),
                                style={"flex": 2, "minWidth": "20px"},
                                value=50,
                                type="number",
                                min=1,
                                max=round(self.surface_geometry["ymax"])
                                - round(self.surface_geometry["ymin"]),
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ],
            ),
            # Well
            html.Div(
                style={
                    "display": "none",
                },
                id=self.register_component_unique_id(IntersectionControls.Ids.WELL_BOX),
                children=wcc.Dropdown(
                    label="Well",
                    id=self.register_component_unique_id(IntersectionControls.Ids.WELL),
                    options=[
                        {"label": well, "value": well} for well in self.well_names
                    ],
                    value=self.well_names[0],
                    clearable=False,
                ),
            ),
            # Surface attr
            wcc.Dropdown(
                label="Surface attribute",
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.SURFACE_ATTR
                ),
                options=[
                    {"label": attribute, "value": attribute}
                    for attribute in self.surface_attributes
                ],
                value=self.surface_attributes[0],
                clearable=False,
                multi=False,
            ),
            # Surface names
            wcc.SelectWithLabel(
                label="Surface names",
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.SURFACE_NAMES
                ),
                options=[
                    {"label": attribute, "value": attribute}
                    for attribute in self.surface_names
                ],
                value=self.surface_names,
                multi=True,
                size=min(len(self.surface_names), 5),
            ),
            # Ensembles
            html.Div(
                style={
                    "marginTop": "5px",
                    "display": ("inline" if len(self.ensembles) > 1 else "none"),
                },
                children=wcc.SelectWithLabel(
                    label="Ensembles",
                    id=self.register_component_unique_id(
                        IntersectionControls.Ids.ENSEMBLES
                    ),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=[self.ensembles[0] if self.ensembles else None],
                    size=min(len(self.ensembles), 3),
                ),
            ),
            # Show surfaces
            wcc.Checklist(
                label="Show surfaces",
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.SHOW_SURFACES
                ),
                options=[
                    {"label": "Mean", "value": "Mean"},
                    {"label": "Min", "value": "Min"},
                    {"label": "Max", "value": "Max"},
                    {"label": "Realizations", "value": "Realizations"},
                    {
                        "label": "Uncertainty envelope",
                        "value": "Uncertainty envelope",
                    },
                ],
                value=["Uncertainty envelope"],
            ),
            # Update intersection button ----------------------
            html.Button(
                "Update intersection",
                className="webviz-structunc-blue-apply-btn",
                id=self.register_component_unique_id(
                    IntersectionControls.Ids.UPDATE_INTERSECTION
                ),
            ),
            # Uncertainty table button --------------------------
            # open_dialog_layout(
            #     dialog_id="uncertainty-table",
            #     uuid=get_uuid("dialog"),
            #     title="Uncertainty table",
            # ),
            # -Settings
            wcc.Selectors(
                open_details=False,
                label="⚙️ Settings",
                children=[
                    html.Div(
                        children=[
                            wcc.Label(
                                "Resolution (m) ",
                            ),
                            dcc.Input(
                                className="webviz-structunc-range-input",
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.RESOLUTION
                                ),
                                type="number",
                                required=True,
                                value=10,
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                    html.Div(
                        children=[
                            wcc.Label(
                                "Extension (m) ",
                            ),
                            dcc.Input(
                                className="webviz-structunc-range-input",
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.EXTENSION
                                ),
                                type="number",
                                step=25,
                                required=True,
                                value=500,
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                    html.Div(
                        style={"margin-top": "10px"},
                        children=[
                            wcc.Label("Depth range settings:"),
                            wcc.FlexBox(
                                style={"display": "flex"},
                                children=[
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            IntersectionControls.Ids.Z_RANGE_MIN
                                        ),
                                        style={"flex": 1, "minWidth": "70px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Min",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                    dcc.Input(
                                        id=self.register_component_unique_id(
                                            IntersectionControls.Ids.Z_RANGE_MAX
                                        ),
                                        style={"flex": 1, "minWidth": "70px"},
                                        type="number",
                                        value=None,
                                        debounce=True,
                                        placeholder="Max",
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                            ),
                            wcc.RadioItems(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.TRUNKATE_LOCK
                                ),
                                options=[
                                    {
                                        "label": "Truncate range",
                                        "value": "truncate",
                                    },
                                    {
                                        "label": "Lock range",
                                        "value": "lock",
                                    },
                                ],
                                value="truncate",
                            ),
                            wcc.Checklist(
                                id=self.register_component_unique_id(
                                    IntersectionControls.Ids.KEEP_ZOOM
                                ),
                                options=[
                                    {
                                        "label": "Keep zoom state",
                                        "value": "uirevision",
                                    },
                                ],
                                value=[],
                            ),
                        ],
                    ),
                    # open_dialog_layout(
                    #     dialog_id="color",
                    #     uuid=get_uuid("dialog"),
                    #     title="Intersection colors",
                    # ),
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SOURCE), "data"),
            Output(self.get_store_unique_id(PluginIds.Stores.FIRST_CALL), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.SOURCE).to_string(),
                "value",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.FIRST_CALL), "value")
        )
        def _set_source_and_first(src: str, first: int) -> Tuple[str, int]:
            if first != 1:
                return (src, 1)
            return (src)
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.INIT_INTERSECTION_LAYOUT), "data"),
            Output(self.get_store_unique_id(PluginIds.Stores.REAL_STORE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.FIRST_CALL), "value")
        )
        def _set_real_and_layout(first: int) -> Tuple[Optional[dict], List[str]]:
            return (self.initial_settings.get("intersection_layout", {}), self.initial_settings.get("intersection-data", {}).get(
                "realizations", self.realizations) )
        @callback(
            Output(self.component_unique_id(IntersectionControls.Ids.WELL_BOX).to_string(), "style"),
            Output(self.component_unique_id(IntersectionControls.Ids.X_LINE_BOX).to_string(), "style"),
            Output(self.component_unique_id(IntersectionControls.Ids.Y_LINE_BOX).to_string(), "style"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SOURCE),
                "data",
            ),
        )
        def _set_style(source: str) -> Tuple[Dict, Dict, Dict]:
            hide = {"display": "none"}
            show = {"display": "inline"}
            if source == "well":
                return show, hide, hide
            if source == "xline":
                return hide, show, hide
            if source == "yline":
                return hide, hide, show
            return [hide, hide, hide]
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.X_LINE), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.X_LINE).to_string(),
                "value",
            ),
        )
        def _set_x_line(x_line: int) -> int:
            return x_line

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_XLINE), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.X_LINE),
                "data",
            ),
        )
        def _set_map_xline(x_value: Union[float, int]) -> List:
            return [
                [x_value, self.surface_geometry["ymin"]],
                [x_value, self.surface_geometry["ymax"]],
            ]
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.STEP_X), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.STEP_X).to_string(),
                "value",
            ),
        )
        def _set_x_step(x_step: int) -> int:
            return x_step

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.Y_LINE), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.Y_LINE).to_string(),
                "value",
            ),
        )
        def _set_y_line(y_line: int) -> int:
            return y_line

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.MAP_STORED_YLINE), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.Y_LINE),
                "data",
            ),
        )
        def _set_map_yline(y_value: Union[float, int]) -> List:
            return [
                [self.surface_geometry["xmin"], y_value],
                [self.surface_geometry["xmax"], y_value],
            ]

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.STEP_Y), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.STEP_Y).to_string(),
                "value",
            ),
        )
        def _set_y_step(y_step: int) -> int:
            return y_step

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.WELL), "data"),
            Input(
                self.component_unique_id(IntersectionControls.Ids.WELL).to_string(),
                "value",
            ),
        )
        def _set_well(well: str) -> str:
            return well

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTR), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.SURFACE_ATTR
                ).to_string(),
                "value",
            ),
        )
        def _set_surf_attr(surf_attr: str) -> str:
            return surf_attr

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SURFACE_NAMES), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.SURFACE_NAMES
                ).to_string(),
                "value",
            ),
        )
        def _set_surf_names(names: List[str]) -> List[str]:
            return names

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SHOW_SURFACES), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.SHOW_SURFACES
                ).to_string(),
                "value",
            ),
        )
        def _set_surface(surf: List[str]) -> List[str]:
            return surf

        # Buttons
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.RESOLUTION), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.RESOLUTION
                ).to_string(),
                "value",
            ),
        )
        def _set_resolution(res: int) -> int:
            return res

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.EXTENSION), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.EXTENSION
                ).to_string(),
                "value",
            ),
        )
        def _set_extension(ext: int) -> int:
            return ext

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MIN), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.Z_RANGE_MIN
                ).to_string(),
                "value",
            ),
        )
        def _set_min(min: int) -> int:
            return min

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.Z_RANGE_MAX), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.Z_RANGE_MAX
                ).to_string(),
                "value",
            ),
        )
        def _set_max(max: int) -> int:
            return max

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.TRUNKATE_LOCK), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.TRUNKATE_LOCK
                ).to_string(),
                "value",
            ),
        )
        def _set_trunk(trunk: str) -> str:
            return trunk

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.KEEP_ZOOM), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.KEEP_ZOOM
                ).to_string(),
                "value",
            ),
        )
        def _set_keep_zoom(keep: str) -> str:
            return keep
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
            Input(
                self.component_unique_id(
                    IntersectionControls.Ids.ENSEMBLES
                ).to_string(),
                "value",
            ),
        )
        def _set_ensembles(ens: List[str]) -> List[str]:
            return ens
        @callback(
            Output(self.component_unique_id(
                    IntersectionControls.Ids.UPDATE_INTERSECTION
                ).to_string(), "style"),
            Output(
                self.get_store_unique_id(PluginIds.Stores.STORED_MANUAL_UPDATE_OPTIONS),
                "data",
            ),
            Input(self.component_unique_id(
                    IntersectionControls.Ids.UPDATE_INTERSECTION
                ).to_string(), "n_clicks"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_ATTR),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SURFACE_NAMES), "data"
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SHOW_SURFACES),
                "data",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.RESOLUTION), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.EXTENSION), "data"),
            State(
                self.get_store_unique_id(PluginIds.Stores.STORED_MANUAL_UPDATE_OPTIONS),
                "data",
            ),
        )
        def _update_apply_button(
            _apply_click: Optional[int],
            surfaceattribute: str,
            surfacenames: List[str],
            statistics: List[str],
            ensembles: str,
            resolution: float,
            extension: int,
            previous_settings: Dict,
        ) -> Tuple[Dict, Dict]:

            ctx = callback_context.triggered[0]
            color_list = self.color_picker._dframe['COLOR'].tolist()
            new_settings = {
                "surface_attribute": surfaceattribute,
                "surface_names": surfacenames,
                "calculation": statistics,
                "ensembles": ensembles,
                "resolution": resolution,
                "extension": extension,
                "colors": color_list,
            }
            # store selected settings if initial callback or apply button is pressed
            if (
                "apply-intersection-data-selections" in ctx["prop_id"]
                or ctx["prop_id"] == "."
            ):
                return {"background-color": "#E8E8E8"}, new_settings

            element = (
                "colors"
                if "colorpicker" in ctx["prop_id"]
                else json.loads(ctx["prop_id"].replace(".value", "")).get("element")
            )
            if new_settings[element] != previous_settings[element]:
                return {"background-color": "#7393B3", "color": "#fff"}, previous_settings
            return {"background-color": "#E8E8E8"}, previous_settings


        # Button
