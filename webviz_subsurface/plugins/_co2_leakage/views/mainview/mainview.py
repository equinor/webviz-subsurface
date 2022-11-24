from typing import Any, Dict, List

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_subsurface_components import DeckGLMap


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

    def __init__(self, color_scales: List[Dict[str, Any]]) -> None:
        super().__init__()
        self._color_scales = color_scales

    def inner_layout(self) -> Component:
        return html.Div(
            [
                wcc.Frame(
                    # id=self.register_component_unique_id(LayoutElements.MAP_VIEW),
                    color="white",
                    highlight=False,
                    children=[
                        html.Div(
                            [
                                DeckGLMap(
                                    id=self.register_component_unique_id(
                                        self.Ids.DECKGL_MAP
                                    ),
                                    layers=[],
                                    coords={"visible": True},
                                    scale={"visible": True},
                                    toolbar={"visible": True},
                                    coordinateUnit="m",
                                    colorTables=self._color_scales,
                                ),
                            ],
                            style={
                                "padding": "1vh",
                                "height": "37vh",
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
                        "height": "47vh",
                    },
                ),
                wcc.Frame(
                    # id=get_uuid(LayoutElements.PLOT_VIEW),
                    style={
                        "height": "33vh",
                        "display": "flex",
                        "flexDirection": "row",
                        "justifyContent": "space-evenly",
                    },
                    children=SummaryGraphLayout(
                        self.register_component_unique_id(self.Ids.BAR_PLOT),
                        self.register_component_unique_id(self.Ids.TIME_PLOT),
                    ).children,
                ),
            ],
            style={
                "flex": 3,
                "display": "flex",
                "flexDirection": "column",
            },
        )


class SummaryGraphLayout(html.Div):
    def __init__(self, bar_plot_id: str, time_plot_id: str, **kwargs: Dict) -> None:
        super().__init__(
            children=[
                wcc.Graph(
                    id=bar_plot_id,
                    figure=go.Figure(),
                    config={
                        "displayModeBar": False,
                    },
                ),
                wcc.Graph(
                    id=time_plot_id,
                    figure=go.Figure(),
                    config={
                        "displayModeBar": False,
                    },
                ),
            ],
            **kwargs,
        )
