from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    callback,
    callback_context,
    dcc,
    html,
    no_update,
)
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_grid_provider import (
    CellFilter,
    EnsembleGridProvider,
)
from webviz_subsurface.plugins._grid_viewer_fmu._layout_elements import ElementIds
from webviz_subsurface.plugins._grid_viewer_fmu._types import GRIDDIRECTION


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class GridFilter(SettingsGroupABC):
    def __init__(
        self, grid_provider: EnsembleGridProvider, initial_grid_filter: Dict[str, int]
    ) -> None:
        super().__init__("Grid IJK Filter")
        self.grid_provider = grid_provider
        initial_grid = grid_provider.get_3dgrid(grid_provider.realizations()[0])
        self.initial_grid_filter = initial_grid_filter
        self.grid_dimensions = (
            CellFilter(
                i_min=1,
                j_min=1,
                k_min=1,
                i_max=initial_grid.dimensions[0],
                j_max=initial_grid.dimensions[1],
                k_max=initial_grid.dimensions[2],
            )
            if initial_grid
            else CellFilter(i_min=1, j_min=1, k_min=1, i_max=1, j_max=1, k_max=1)
        )

    def layout(self) -> List[Component]:

        return [
            html.Div(
                style={"backgroundColor": "white"},
                children=[
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.i_min,
                        selected_min_val=self.initial_grid_filter.get("i_start", None),
                        selected_max_val=self.initial_grid_filter.get("i_width", None),
                        max_val=self.grid_dimensions.i_max,
                        direction=GRIDDIRECTION.I,
                    ),
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.j_min,
                        selected_min_val=self.initial_grid_filter.get("j_start", None),
                        selected_max_val=self.initial_grid_filter.get("j_width", None),
                        max_val=self.grid_dimensions.j_max,
                        direction=GRIDDIRECTION.J,
                    ),
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.k_min,
                        selected_min_val=self.initial_grid_filter.get("k_start", None),
                        selected_max_val=self.initial_grid_filter.get("k_width", None),
                        max_val=self.grid_dimensions.k_max,
                        direction=GRIDDIRECTION.K,
                    ),
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": MATCH,
                    "component": "input",
                    "component2": MATCH,
                },
                "value",
            ),
            Output(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": MATCH,
                    "component": "slider",
                    "component2": MATCH,
                },
                "value",
            ),
            Input(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": MATCH,
                    "component": "input",
                    "component2": MATCH,
                },
                "value",
            ),
            Input(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": MATCH,
                    "component": "slider",
                    "component2": MATCH,
                },
                "value",
            ),
        )
        def _synchronize_crop_slider_and_input(
            input_val: int, slider_val: int
        ) -> Tuple[Any, Any]:
            trigger_id = callback_context.triggered[0]["prop_id"].split(".")[0]
            if "slider" in trigger_id:
                return slider_val, no_update
            return no_update, input_val

        @callback(
            Output(self.get_store_unique_id(ElementIds.IJK_CROP_STORE), "data"),
            Input(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": ALL,
                    "component": "input",
                    "component2": "start",
                },
                "value",
            ),
            Input(
                {
                    "id": self.get_unique_id().to_string(),
                    "direction": ALL,
                    "component": "input",
                    "component2": "width",
                },
                "value",
            ),
        )
        def _store_grid_range_from_crop_widget(
            input_vals: List[int], width_vals: List[int]
        ) -> List[List[int]]:
            """Converts the ijk indices from one-based to zero-based and stores
            the filter range in a dcc.Store."""

            if not input_vals or not width_vals:
                return no_update
            if any(val is None for val in input_vals + width_vals):
                return no_update
            return [
                [val - 1, val + width - 2] for val, width in zip(input_vals, width_vals)
            ]


def crop_widget(
    widget_id: str,
    min_val: int,
    max_val: int,
    direction: str,
    selected_min_val: Optional[int] = None,
    selected_max_val: Optional[int] = None,
) -> html.Div:

    return html.Div(
        style={"borderBottom": "1px outset", "marginBottom": "15px"}
        if direction != GRIDDIRECTION.K
        else {},
        children=[
            html.Div(
                style={
                    "display": "grid",
                    "marginBotton": "0px",
                    "gridTemplateColumns": "2fr 1fr 8fr",
                },
                children=[
                    wcc.Label(
                        children=f"{direction} Start",
                        style={
                            "fontSize": "0.7em",
                            "fontWeight": "bold",
                            "marginRight": "5px",
                        },
                    ),
                    dcc.Input(
                        style={"width": "50px", "height": "10px"},
                        id={
                            "id": widget_id,
                            "direction": direction,
                            "component": "input",
                            "component2": "start",
                        },
                        type="number",
                        persistence=True,
                        persistence_type="session",
                        minLength=1,
                        value=selected_min_val if selected_min_val else min_val,
                        min=min_val,
                        max=max_val,
                    ),
                    wcc.Slider(
                        id={
                            "id": widget_id,
                            "direction": direction,
                            "component": "slider",
                            "component2": "start",
                        },
                        marks={val: val for val in [min_val, max_val]},
                        min=min_val,
                        max=max_val,
                        value=selected_min_val if selected_min_val else min_val,
                        step=1,
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "grid",
                    "marginTop": "0px",
                    "padding": "0px",
                    "gridTemplateColumns": "2fr 1fr 8fr",
                },
                children=[
                    wcc.Label(
                        children="Width",
                        style={
                            "fontSize": "0.7em",
                            "textAlign": "right",
                            "marginRight": "5px",
                        },
                    ),
                    dcc.Input(
                        style={"width": "50px", "height": "10px"},
                        id={
                            "id": widget_id,
                            "direction": direction,
                            "component": "input",
                            "component2": "width",
                        },
                        type="number",
                        minLength=1,
                        persistence=True,
                        persistence_type="session",
                        value=selected_max_val if selected_max_val else max_val,
                        min=1,
                        max=max_val,
                    ),
                    wcc.Slider(
                        id={
                            "id": widget_id,
                            "direction": direction,
                            "component": "slider",
                            "component2": "width",
                        },
                        min=1,
                        marks={val: "" for val in [min_val, max_val]},
                        max=max_val,
                        value=selected_max_val if selected_max_val else max_val,
                        step=1,
                    ),
                ],
            ),
        ],
    )
