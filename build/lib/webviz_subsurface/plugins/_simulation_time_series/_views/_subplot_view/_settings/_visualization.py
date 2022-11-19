from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._types import (
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)


class VisualizationSettings(SettingsGroupABC):
    class Ids(StrEnum):
        VISUALIZATION_RADIO_ITEMS = "visualization-radio-items"
        PLOT_TRACE_OPTIONS_CHECKLIST = "plot-trace-options-checklist"
        PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot-statistics-options-checklist"
        PLOT_FANCHART_OPTIONS_CHECKLIST = "plot-fanchart-options-checklist"
        PLOT_OPTIONS = "plot-options"

    def __init__(self, selected_visualization: VisualizationOptions) -> None:
        super().__init__("Visualization")
        self._selected_visualization = selected_visualization

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    VisualizationSettings.Ids.VISUALIZATION_RADIO_ITEMS
                ),
                options=[
                    {
                        "label": "Individual realizations",
                        "value": VisualizationOptions.REALIZATIONS,
                    },
                    {
                        "label": "Statistical lines",
                        "value": VisualizationOptions.STATISTICS,
                    },
                    {
                        "label": "Statistical fanchart",
                        "value": VisualizationOptions.FANCHART,
                    },
                    {
                        "label": "Statistics + Realizations",
                        "value": VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    },
                ],
                value=self._selected_visualization,
            ),
            wcc.LabeledContainer(
                label="Options",
                id=self.register_component_unique_id(
                    VisualizationSettings.Ids.PLOT_OPTIONS
                ),
                children=self._plot_options_layout(
                    selected_visualization=self._selected_visualization,
                ),
            ),
        ]

    def _plot_options_layout(
        self,
        selected_visualization: VisualizationOptions,
    ) -> html.Div:
        return html.Div(
            children=[
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        VisualizationSettings.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"},
                    options=[
                        {"label": "History", "value": TraceOptions.HISTORY},
                        {
                            "label": "Observation",
                            "value": TraceOptions.OBSERVATIONS,
                        },
                    ],
                    value=[TraceOptions.HISTORY, TraceOptions.OBSERVATIONS],
                ),
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        VisualizationSettings.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"}
                    if selected_visualization
                    in [
                        VisualizationOptions.STATISTICS,
                        VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    ]
                    else {"display": "none"},
                    options=[
                        {"label": "Mean", "value": StatisticsOptions.MEAN},
                        {
                            "label": "P10 (high)",
                            "value": StatisticsOptions.P10,
                        },
                        {
                            "label": "P50 (median)",
                            "value": StatisticsOptions.P50,
                        },
                        {
                            "label": "P90 (low)",
                            "value": StatisticsOptions.P90,
                        },
                        {"label": "Maximum", "value": StatisticsOptions.MAX},
                        {"label": "Minimum", "value": StatisticsOptions.MIN},
                    ],
                    value=[
                        StatisticsOptions.MEAN,
                        StatisticsOptions.P10,
                        StatisticsOptions.P90,
                    ],
                ),
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        VisualizationSettings.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"}
                    if VisualizationOptions.FANCHART == selected_visualization
                    else {"display": "none"},
                    options=[
                        {
                            "label": FanchartOptions.MEAN,
                            "value": FanchartOptions.MEAN,
                        },
                        {
                            "label": FanchartOptions.P10_P90,
                            "value": FanchartOptions.P10_P90,
                        },
                        {
                            "label": FanchartOptions.MIN_MAX,
                            "value": FanchartOptions.MIN_MAX,
                        },
                    ],
                    value=[
                        FanchartOptions.MEAN,
                        FanchartOptions.P10_P90,
                        FanchartOptions.MIN_MAX,
                    ],
                ),
            ],
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    VisualizationSettings.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Output(
                self.component_unique_id(
                    VisualizationSettings.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Input(
                self.component_unique_id(
                    VisualizationSettings.Ids.VISUALIZATION_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_statistics_options_layout(
            selected_visualization: VisualizationOptions,
        ) -> List[dict]:
            """Only show statistics checklist if in statistics mode"""

            def get_style(visualization_options: List[VisualizationOptions]) -> dict:
                return (
                    {"display": "block"}
                    if selected_visualization in visualization_options
                    else {"display": "none"}
                )

            statistics_options_style = get_style(
                [
                    VisualizationOptions.STATISTICS,
                    VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                ]
            )
            fanchart_options_style = get_style([VisualizationOptions.FANCHART])

            return [statistics_options_style, fanchart_options_style]
