from typing import Any, Dict, List

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_subsurface_components import DashSubsurfaceViewer


class MainView(ViewABC):
    class Ids(StrEnum):
        MAIN_ELEMENT = "main-element"

    def __init__(self, color_scales: List[Dict[str, Any]]):
        super().__init__("Main View")
        self._view_element = MapViewElement(color_scales)
        self.add_view_element(self._view_element, self.Ids.MAIN_ELEMENT)


class MapViewElement(ViewElementABC):
    class Ids(StrEnum):
        DECKGL_MAP = "deck-gl-map"
        DATE_SLIDER = "date-slider"
        DATE_WRAPPER = "date-wrapper"
        BAR_PLOT = "bar-plot"
        TIME_PLOT = "time-plot"
        TIME_PLOT_ONE_REAL = "time-plot-one-realization"
        BAR_PLOT_ORDER = "bar-plot-order"
        CONTAINMENT_COLORS = "containment-order"
        SIZE_SLIDER = "size-slider"
        TOP_ELEMENT = "top-element"
        BOTTOM_ELEMENT = "bottom-element"

    def __init__(self, color_scales: List[Dict[str, Any]]) -> None:
        super().__init__()
        self._color_scales = color_scales

    def inner_layout(self) -> Component:
        return html.Div(
            [
                wcc.Frame(
                    # id=self.register_component_unique_id(LayoutElements.MAP_VIEW),
                    id=self.register_component_unique_id(self.Ids.TOP_ELEMENT),
                    color="white",
                    highlight=False,
                    children=[
                        html.Div(
                            [
                                DashSubsurfaceViewer(
                                    id=self.register_component_unique_id(
                                        self.Ids.DECKGL_MAP
                                    ),
                                    layers=[],
                                    coords={"visible": True},
                                    scale={"visible": True},
                                    coordinateUnit="m",
                                    colorTables=self._color_scales,
                                ),
                            ],
                            style={
                                "padding": "1%",
                                "height": "80%",
                                "position": "relative",
                            },
                        ),
                        html.Div(
                            wcc.Slider(
                                id=self.register_component_unique_id(
                                    self.Ids.DATE_SLIDER
                                ),
                                step=None,
                                marks={0: ""},
                                value=0,
                            ),
                            id=self.register_component_unique_id(self.Ids.DATE_WRAPPER),
                        ),
                    ],
                    style={
                        "height": "43vh",
                    },
                ),
                wcc.Frame(
                    # id=get_uuid(LayoutElements.PLOT_VIEW),
                    id=self.register_component_unique_id(self.Ids.BOTTOM_ELEMENT),
                    style={
                        "height": "37vh",
                    },
                    children=[
                        html.Div(
                            _summary_graph_layout(
                                self.register_component_unique_id(self.Ids.BAR_PLOT),
                                self.register_component_unique_id(self.Ids.TIME_PLOT),
                                self.register_component_unique_id(
                                    self.Ids.TIME_PLOT_ONE_REAL
                                ),
                            )
                        ),
                    ],
                ),
                html.Div(
                    [
                        wcc.Slider(
                            id=self.register_component_unique_id(self.Ids.SIZE_SLIDER),
                            min=1,
                            max=79,
                            step=2,
                            value=37,
                            vertical=False,
                            marks={
                                # 1: "Top",
                                37: "Drag to scale the size of the containment plots",
                                # 79: "Bottom",
                            },
                        ),
                    ],
                    style={
                        "width": "100%",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "height": "90vh",
            },
        )


def _summary_graph_layout(
    bar_plot_id: str,
    time_plot_id: str,
    time_plot_one_realization_id: str,
) -> List:
    return [
        wcc.Tabs(
            id="TAB",
            value="tab-1",
            children=[
                wcc.Tab(
                    label="End-state containment (all realizations)",
                    value="tab-1",
                    children=[
                        html.Div(
                            wcc.Graph(
                                id=bar_plot_id,
                                figure=go.Figure(),
                                config={
                                    "displayModeBar": False,
                                },
                            ),
                        ),
                    ],
                ),
                wcc.Tab(
                    label="Containment over time (all realizations)",
                    value="tab-2",
                    children=[
                        html.Div(
                            wcc.Graph(
                                id=time_plot_id,
                                figure=go.Figure(),
                                config={
                                    "displayModeBar": False,
                                },
                            ),
                        ),
                    ],
                ),
                wcc.Tab(
                    label="Containment over time (one realization)",
                    value="tab-3",
                    children=[
                        html.Div(
                            wcc.Graph(
                                id=time_plot_one_realization_id,
                                figure=go.Figure(),
                                config={
                                    "displayModeBar": False,
                                },
                            ),
                        ),
                    ],
                ),
            ],
        ),
    ]
