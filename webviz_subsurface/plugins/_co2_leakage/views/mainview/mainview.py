
import plotly.graph_objects as go
from dash import html, dcc
import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC

from webviz_subsurface_components import DeckGLMap

from webviz_subsurface.plugins._map_viewer_fmu.color_tables import default_color_tables


INITIAL_BOUNDS = (0, 0, 1, 1)


class MainView(ViewABC):
    class Ids:
        MAIN_ELEMENT = "main-element"

    def __init__(self):
        super().__init__("Main View")
        self._view_element = MapViewElement()
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
                                    id=self.register_component_unique_id(self.Ids.DECKGL_MAP),
                                    layers=[],
                                    bounds=INITIAL_BOUNDS,
                                    coords={"visible": True},
                                    scale={"visible": True},
                                    toolbar={"visible": True},
                                    coordinateUnit="m",
                                    colorTables=_color_tables(),
                                    zoom=-7,
                                ),
                            ],
                            style=self.Style.MAP_WRAPPER,
                        ),
                        html.Div(
                            wcc.Slider(
                                id=self.register_component_unique_id(self.Ids.DATE_SLIDER),
                                step=None,
                                marks={0: ''},
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
                    ).children
                )
            ],
            style=self.Style.CONTENT_PARENT
        )


class SummaryGraphLayout(html.Div):
    def __init__(self, bar_plot_id, time_plot_id, **kwargs):
        super().__init__(
            children=[
                wcc.Graph(
                    id=bar_plot_id,
                    figure=go.Figure(),
                    config={
                        "displayModeBar": False,
                    }
                ),
                wcc.Graph(
                    id=time_plot_id,
                    figure=go.Figure(),
                    config={
                        "displayModeBar": False,
                    }
                ),
            ],
            **kwargs,
        )


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
