from typing import Any, Dict, List

import dash_daq as daq
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

TAB_STYLE = {"flex": "1 1 auto", "width": "auto"}
DATE_SLIDER_HEIGHT = 70  # px
DATE_SLIDER_STYLE = {"height": f"{DATE_SLIDER_HEIGHT}px", "flexShrink": 0}


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
        MAP_ANNOTATIONS = "map-annotations"
        DATE_SLIDER = "date-slider"
        DATE_WRAPPER = "date-wrapper"
        BAR_PLOT = "bar-plot"
        TIME_PLOT = "time-plot"
        TIME_PLOT_LINES = "time-plot-lines"
        TIME_PLOT_LINES_WRAPPER = "time-plot-lines-wrapper"
        PROBABILITY_PLOT = "probability-plot"
        BOX_PLOT = "box-plot"
        OUTLIER_TOGGLE = "outlier-toggle"
        BAR_PLOT_ORDER = "bar-plot-order"
        CONTAINMENT_COLORS = "containment-order"
        SIZE_SLIDER = "size-slider"
        TOP_ELEMENT = "top-element"
        BOTTOM_ELEMENT = "bottom-element"
        LEGEND_DATA_STORE = "legend-data-store"
        PLOT_GENERATION_STORE = "plot-generation-store"
        SUMMARY_TABS = "summary-tabs"
        CSV_EXPORT_BUTTON = "csv-export-button"
        DOWNLOAD_CSV = "download-csv"

    def __init__(
        self, color_scales: List[Dict[str, Any]], content: Dict[str, bool]
    ) -> None:
        super().__init__()
        self._color_scales = color_scales
        self._content = content

    def inner_layout(self) -> Component:  # type: ignore[override]
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
                                    showReadout=True,
                                    pickingDepth=1,
                                    scale={"visible": True},
                                    coordinateUnit="m",
                                    colorTables=self._color_scales,
                                ),
                                html.Div(
                                    id=self.register_component_unique_id(
                                        self.Ids.MAP_ANNOTATIONS
                                    ),
                                    style={
                                        "position": "absolute",
                                        "inset": "1%",
                                        "pointerEvents": "none",
                                        "zIndex": 10,
                                    },
                                ),
                            ],
                            style={
                                "padding": "1%",
                                "height": "100%",
                                "boxSizing": "border-box",
                                "position": "relative",
                            },
                        ),
                    ],
                    style={
                        "height": "43vh" if self._content["any_table"] else "100%",
                    },
                )
            )
        layout_elements.append(
            html.Div(
                wcc.Slider(
                    id=self.register_component_unique_id(self.Ids.DATE_SLIDER),
                    step=None,
                    marks={0: ""},
                    value=0,
                ),
                id=self.register_component_unique_id(self.Ids.DATE_WRAPPER),
                style=DATE_SLIDER_STYLE,
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
                                    self.Ids.TIME_PLOT_LINES
                                ),
                                self.register_component_unique_id(
                                    self.Ids.TIME_PLOT_LINES_WRAPPER
                                ),
                                self.register_component_unique_id(
                                    self.Ids.PROBABILITY_PLOT
                                ),
                                self.register_component_unique_id(
                                    self.Ids.BOX_PLOT,
                                ),
                                self.register_component_unique_id(
                                    self.Ids.OUTLIER_TOGGLE
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
                    data=LegendData(  # type: ignore[arg-type]
                        bar_legendonly=None,
                        time_legendonly=None,
                        probability_legendonly=None,
                        box_legendonly=None,
                    ),
                )
            )
            layout_elements.append(
                dcc.Store(
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_GENERATION_STORE
                    ),
                    data={},
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
                                37: "Drag to scale the relative size between the map and the graphs",
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
                "flex-direction": "column",
                "height": "90vh",
            },
        )


def _plot_toggle(toggle_id: str, left_label: str, right_label: str) -> html.Div:
    return html.Div(
        [
            html.Span(left_label),
            daq.ToggleSwitch(
                id=toggle_id,
                value=False,  # True = right_label
                size=30,
                style={"position": "relative", "top": "-5px"},
            ),
            html.Span(right_label),
        ],
        style={
            "position": "absolute",
            "top": "5px",
            "right": "10px",
            "zIndex": 1000,
            "display": "flex",
            "alignItems": "center",
            "gap": "6px",
            "fontSize": "15px",
        },
    )


def _summary_graph_layout(
    bar_plot_id: str,
    time_plot_id: str,
    time_plot_lines_id: str,
    time_plot_lines_wrapper_id: str,
    probability_plot_id: str,
    box_plot_id: str,
    outlier_toggle_id: str,
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
                            style=TAB_STYLE,
                            selected_style=TAB_STYLE,
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
                            label="Time plot",
                            value=MainTabOption.CONTAINMENT_OVER_TIME,
                            style=TAB_STYLE,
                            selected_style=TAB_STYLE,
                            children=[
                                html.Div(
                                    [
                                        html.Div(
                                            _plot_toggle(
                                                time_plot_lines_id,
                                                "Mean/P10/P90",
                                                "Realizations",
                                            ),
                                            id=time_plot_lines_wrapper_id,
                                        ),
                                        wcc.Graph(
                                            id=time_plot_id,
                                            figure=go.Figure(),
                                            config={
                                                "displayModeBar": False,
                                            },
                                        ),
                                    ],
                                    style={"position": "relative"},
                                ),
                            ],
                        ),
                        wcc.Tab(
                            label="Probability plot",
                            value=MainTabOption.PROBABILITY,
                            style=TAB_STYLE,
                            selected_style=TAB_STYLE,
                            children=[
                                html.Div(
                                    wcc.Graph(
                                        id=probability_plot_id,
                                        figure=go.Figure(),
                                        config={
                                            "displayModeBar": False,
                                        },
                                    ),
                                ),
                            ],
                        ),
                        wcc.Tab(
                            label="Box plot",
                            value=MainTabOption.BOX_PLOT,
                            style=TAB_STYLE,
                            selected_style=TAB_STYLE,
                            children=[
                                html.Div(
                                    [
                                        _plot_toggle(
                                            outlier_toggle_id,
                                            "Show outliers",
                                            "Show all points",
                                        ),
                                        wcc.Graph(
                                            id=box_plot_id,
                                            figure=go.Figure(),
                                            config={
                                                "displayModeBar": False,
                                            },
                                        ),
                                    ],
                                    style={"position": "relative"},
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
