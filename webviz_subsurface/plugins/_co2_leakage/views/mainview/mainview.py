from typing import Any, Dict, List

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_subsurface_components import DeckGLMap

INITIAL_BOUNDS = (0, 0, 1, 1)


class MainView(ViewABC):
    class Ids:
        MAIN_ELEMENT = "main-element"

    def __init__(self, color_scales: List[Dict[str, Any]]):
        super().__init__("Main View")
        self._view_element = MapViewElement(color_scales)
        self.add_view_element(self._view_element, self.Ids.MAIN_ELEMENT)


class MapViewElement(ViewElementABC):
    class Ids:
        DECKGL_MAP = "deck-gl-map"
        DATE_SLIDER = "date-slider"
        DATE_WRAPPER = "date-wrapper"
        BAR_PLOT = "bar-plot"
        TIME_PLOT = "time-plot"

    class Style:
        MAP_WRAPPER = {
            "padding": "1vh",
            "height": "37vh",
            "position": "relative",
        }
        MAP_VIEW = {
            "height": "47vh",
        }
        PLOT_VIEW = {
            "height": "33vh",
            "display": "flex",
            "flexDirection": "row",
            "justifyContent": "space-evenly",
        }
        CONTENT_PARENT = {
            "flex": 3,
            "display": "flex",
            "flexDirection": "column",
        }

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
                                    bounds=INITIAL_BOUNDS,
                                    coords={"visible": True},
                                    scale={"visible": True},
                                    toolbar={"visible": True},
                                    coordinateUnit="m",
                                    colorTables=self._color_scales,
                                    zoom=-7,
                                ),
                            ],
                            style=self.Style.MAP_WRAPPER,
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
                    style=self.Style.MAP_VIEW,
                ),
                wcc.Frame(
                    # id=get_uuid(LayoutElements.PLOT_VIEW),
                    style=self.Style.PLOT_VIEW,
                    children=SummaryGraphLayout(
                        self.register_component_unique_id(self.Ids.BAR_PLOT),
                        self.register_component_unique_id(self.Ids.TIME_PLOT),
                    ).children,
                ),
            ],
            style=self.Style.CONTENT_PARENT,
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
