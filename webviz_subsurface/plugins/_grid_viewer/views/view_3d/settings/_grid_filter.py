from typing import List, Tuple, Dict, Optional, Any

from dash.development.base_component import Component
from dash import (
    html,
    dcc,
    Input,
    Output,
    callback,
    no_update,
    ALL,
    MATCH,
    callback_context,
)
import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProvider,
    CellFilter,
)

from webviz_subsurface.plugins._grid_viewer._types import GRID_DIRECTION
from webviz_subsurface.plugins._grid_viewer._layout_elements import ElementIds


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class GridFilter(SettingsGroupABC):
    def __init__(self, grid_provider: EnsembleGridProvider) -> None:
        super().__init__("Grid IJK Filter")
        self.grid_provider = grid_provider
        initial_grid = grid_provider.get_3dgrid(grid_provider.realizations()[0])
        self.grid_dimensions = CellFilter(
            i_min=0,
            j_min=0,
            k_min=0,
            i_max=initial_grid.dimensions[0] - 1,
            j_max=initial_grid.dimensions[1] - 1,
            k_max=initial_grid.dimensions[2] - 1,
        )

    def layout(self) -> List[Component]:

        return [
            wcc.Selectors(
                label="Range filters",
                children=[
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.i_min,
                        max_val=self.grid_dimensions.i_max,
                        direction=GRID_DIRECTION.I,
                    ),
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.j_min,
                        max_val=self.grid_dimensions.j_max,
                        direction=GRID_DIRECTION.J,
                    ),
                    crop_widget(
                        widget_id=self.get_unique_id().to_string(),
                        min_val=self.grid_dimensions.k_min,
                        max_val=self.grid_dimensions.k_max,
                        max_width=self.grid_dimensions.k_min,
                        direction=GRID_DIRECTION.K,
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
            Output(
                self.get_store_unique_id(ElementIds.GridFilter.IJK_CROP_STORE), "data"
            ),
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
            if not input_vals or not width_vals:
                return no_update
            return [
                [val, val + width - 1] for val, width in zip(input_vals, width_vals)
            ]


def crop_widget(
    widget_id: str,
    min_val: int,
    max_val: int,
    direction: str,
    max_width: Optional[int] = None,
) -> html.Div:
    max_width = max_width if max_width else max_val
    return html.Div(
        children=[
            html.Div(
                style={
                    "display": "grid",
                    "marginBotton": "0px",
                    "gridTemplateColumns": f"2fr 1fr 8fr",
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
                        placeholder="Min",
                        persistence=True,
                        persistence_type="session",
                        value=min_val,
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
                        min=min_val,
                        max=max_val,
                        value=min_val,
                        step=1,
                        marks=None,
                    ),
                ],
            ),
            html.Div(
                style={
                    "display": "grid",
                    "marginTop": "0px",
                    "padding": "0px",
                    "gridTemplateColumns": f"2fr 1fr 8fr",
                },
                children=[
                    wcc.Label(
                        children=f"Width",
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
                        placeholder="Min",
                        persistence=True,
                        persistence_type="session",
                        value=max_width,
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
                        max=max_val,
                        value=max_width,
                        step=1,
                        marks=None,
                    ),
                ],
            ),
        ],
    )
