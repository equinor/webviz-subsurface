from typing import Any, Dict, List

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC, ViewElementABC
from webviz_subsurface_components import SubsurfaceViewer

from webviz_subsurface.plugins._co2_migration._types import LegendData
from webviz_subsurface.plugins._co2_migration._utilities.containment_info import (
    MainTabOption,
)


class MainView(ViewABC):
    class Ids(StrEnum):
        MAIN_ELEMENT = "main-element"

    def __init__(self, color_scales: List[Dict[str, Any]], content: Dict[str, bool]):
        super().__init__("Main View")
        self._view_element = MapViewElement(color_scales, content)
        self.add_view_element(self._view_element, self.Ids.MAIN_ELEMENT)


class MapViewElement(ViewElementABC):
    class Ids(StrEnum):
        DECKGL_MAP = "deck-gl-map"
        DATE_SLIDER = "date-slider"
        DATE_WRAPPER = "date-wrapper"
        BAR_PLOT = "bar-plot"
        TIME_PLOT = "time-plot"
        STATISTICS_PLOT = "statistics-plot"
        BAR_PLOT_ORDER = "bar-plot-order"
        CONTAINMENT_COLORS = "containment-order"
        SIZE_SLIDER = "size-slider"
        TOP_ELEMENT = "top-element"
        BOTTOM_ELEMENT = "bottom-element"
        LEGEND_DATA_STORE = "legend-data-store"
        SUMMARY_TABS = "summary-tabs"
        CSV_EXPORT_BUTTON = "csv-export-button"
        DOWNLOAD_CSV = "download-csv"

    def __init__(
        self, color_scales: List[Dict[str, Any]], content: Dict[str, bool]
    ) -> None:
        super().__init__()
        self._color_scales = color_scales
        self._content = content

    def inner_layout(self) -> Component:
        layout_elements = []
        if self._content["maps"]:
            layout_elements.append(
                wcc.Frame(
                    # id=self.register_component_unique_id(LayoutElements.MAP_VIEW),
                    id=self.register_component_unique_id(self.Ids.TOP_ELEMENT),
                    color="white",
                    highlight=False,
                    children=[
                        html.Div(
                            [
                                SubsurfaceViewer(
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
                        "height": "43vh" if self._content["any_table"] else "100%",
                    },
                )
            )
        if self._content["any_table"]:
            layout_elements.append(
                wcc.Frame(
                    # id=get_uuid(LayoutElements.PLOT_VIEW),
                    id=self.register_component_unique_id(self.Ids.BOTTOM_ELEMENT),
                    style={
                        "height": "37vh" if self._content["maps"] else "100%",
                    },
                    children=[
                        html.Div(
                            _summary_graph_layout(
                                self.register_component_unique_id(self.Ids.BAR_PLOT),
                                self.register_component_unique_id(self.Ids.TIME_PLOT),
                                self.register_component_unique_id(
                                    self.Ids.STATISTICS_PLOT
                                ),
                                self.register_component_unique_id(
                                    self.Ids.CSV_EXPORT_BUTTON
                                ),
                                self.register_component_unique_id(
                                    self.Ids.DOWNLOAD_CSV
                                ),
                                self.register_component_unique_id(
                                    self.Ids.SUMMARY_TABS
                                ),
                            )
                        ),
                    ],
                )
            )
            layout_elements.append(
                dcc.Store(
                    id=self.register_component_unique_id(self.Ids.LEGEND_DATA_STORE),
                    data=LegendData(
                        bar_legendonly=None,
                        time_legendonly=None,
                        stats_legendonly=None,
                    ),
                )
            )
        if self._content["maps"] and self._content["any_table"]:
            layout_elements.append(
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
                )
            )
        return html.Div(
            layout_elements,
            style={
                "display": "flex",
                "flexDirection": "column",
                "height": "90vh",
            },
        )


def _summary_graph_layout(
    bar_plot_id: str,
    time_plot_id: str,
    statistics_plot_id: str,
    csv_export_button_id: str,
    download_csv_id: str,
    summary_tabs_id: str,
) -> List:
    return [
        html.Div(
            [
                html.Button(
                    "↓",
                    id=csv_export_button_id,
                    title="Export data in current plot to a CSV file",
                    style={
                        "position": "absolute",
                        "bottom": "5px",
                        "right": "5px",
                        "backgroundColor": "#F4F4F4",
                        "border": "1px solid #B0B0B0",
                        "color": "#606060",
                        "padding": "0",
                        "borderRadius": "4px",
                        "zIndex": "1000",  # Make sure it appears on top
                        "fontSize": "18px",
                        "fontWeight": "bold",
                        "display": "flex",
                        "alignItems": "center",  # Vertical centering
                        "justifyContent": "center",  # Horizontal centering
                        "lineHeight": "1",  # Prevents extra line spacing
                        "textAlign": "center",
                        "width": "32px",
                        "height": "32px",
                        "fontFamily": "Arial, sans-serif",
                    },
                ),
                wcc.Tabs(
                    id=summary_tabs_id,
                    value=MainTabOption.CONTAINMENT_STATE,
                    children=[
                        wcc.Tab(
                            label="Containment state",
                            value=MainTabOption.CONTAINMENT_STATE,
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
                            label="Containment over time",
                            value=MainTabOption.CONTAINMENT_OVER_TIME,
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
                            label="Statistics",
                            value=MainTabOption.STATISTICS,
                            children=[
                                html.Div(
                                    wcc.Graph(
                                        id=statistics_plot_id,
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
            ],
            style={
                "position": "relative",
                "height": "100%",
                "width": "100%",
            },
        ),
        dcc.Download(id=download_csv_id),
    ]
