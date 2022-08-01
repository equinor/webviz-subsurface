import datetime
from typing import List, Optional

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds
from ..types import (
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)
from ..utils import datetime_utils


class VisualizationSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        VISUALIZATION_RADIO_ITEMS = "visualization-radio-items"
        PLOT_TRACE_OPTIONS_CHECKLIST = "plot-trace-options-checklist"
        PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot-statistics-options-checklist"
        PLOT_FANCHART_OPTIONS_CHECKLIST = "plot-fanchart-options-checklist"

    def __init__(self, selected_visualization: VisualizationOptions) -> None:
        super().__init__("Visualization")
        self.selected_visualization = selected_visualization

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    self.Ids.VISUALIZATION_RADIO_ITEMS
                ),
                options=[
                    {
                        "label": "Individual realizations",
                        "value": VisualizationOptions.REALIZATIONS.value,
                    },
                    {
                        "label": "Statistical lines",
                        "value": VisualizationOptions.STATISTICS.value,
                    },
                    {
                        "label": "Statistical fanchart",
                        "value": VisualizationOptions.FANCHART.value,
                    },
                    {
                        "label": "Statistics + Realizations",
                        "value": VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    },
                ],
                value=self.selected_visualization.value,
            ),
            wcc.Selectors(
                label="Options",
                id=self.register_component_unique_id(PluginIds.TourStepIds.OPTIONS),
                children=self.__plot_options_layout(
                    selected_visualization=self.selected_visualization,
                ),
            ),
        ]

    def __plot_options_layout(
        self,
        selected_visualization: VisualizationOptions,
    ) -> html.Div:
        return html.Div(
            children=[
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"},
                    options=[
                        {"label": "History", "value": TraceOptions.HISTORY.value},
                        {
                            "label": "Observation",
                            "value": TraceOptions.OBSERVATIONS.value,
                        },
                    ],
                    value=[TraceOptions.HISTORY.value, TraceOptions.OBSERVATIONS.value],
                ),
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"}
                    if selected_visualization
                    in [
                        VisualizationOptions.STATISTICS,
                        VisualizationOptions.STATISTICS_AND_REALIZATIONS,
                    ]
                    else {"display": "none"},
                    options=[
                        {"label": "Mean", "value": StatisticsOptions.MEAN.value},
                        {
                            "label": "P10 (high)",
                            "value": StatisticsOptions.P10.value,
                        },
                        {
                            "label": "P50 (median)",
                            "value": StatisticsOptions.P50.value,
                        },
                        {
                            "label": "P90 (low)",
                            "value": StatisticsOptions.P90.value,
                        },
                        {"label": "Maximum", "value": StatisticsOptions.MAX.value},
                        {"label": "Minimum", "value": StatisticsOptions.MIN.value},
                    ],
                    value=[
                        StatisticsOptions.MEAN.value,
                        StatisticsOptions.P10.value,
                        StatisticsOptions.P90.value,
                    ],
                ),
                wcc.Checklist(
                    id=self.register_component_unique_id(
                        self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                    ),
                    style={"display": "block"}
                    if VisualizationOptions.FANCHART == selected_visualization
                    else {"display": "none"},
                    options=[
                        {
                            "label": FanchartOptions.MEAN.value,
                            "value": FanchartOptions.MEAN.value,
                        },
                        {
                            "label": FanchartOptions.P10_P90.value,
                            "value": FanchartOptions.P10_P90.value,
                        },
                        {
                            "label": FanchartOptions.MIN_MAX.value,
                            "value": FanchartOptions.MIN_MAX.value,
                        },
                    ],
                    value=[
                        FanchartOptions.MEAN.value,
                        FanchartOptions.P10_P90.value,
                        FanchartOptions.MIN_MAX.value,
                    ],
                ),
            ],
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Output(
                self.component_unique_id(
                    self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                ).to_string(),
                "style",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.VISUALIZATION_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def _update_statistics_options_layout(
            selected_visualization: str,
        ) -> List[dict]:
            """Only show statistics checklist if in statistics mode"""

            # Convert to enum type
            selected_visualization = VisualizationOptions(selected_visualization)

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

        @callback(
            [
                Output(
                    self.component_unique_id(
                        self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                    ).to_string(),
                    "style",
                ),
            ],
            [
                Input(
                    self.get_store_unique_id(PluginIds.Stores.RELATIVE_DATE_DROPDOWN),
                    "data",
                )
            ],
        )
        def _update_trace_options_layout(
            relative_date_value: str,
        ) -> List[dict]:
            """Hide trace options (History and Observation) when relative date is selected"""

            # Convert to Optional[datetime.datime]
            relative_date: Optional[datetime.datetime] = (
                None
                if relative_date_value is None
                else datetime_utils.from_str(relative_date_value)
            )

            if relative_date:
                return [{"display": "none"}]
            return [{"display": "block"}]

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.VISUALIZATION_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.VISUALIZATION_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def _update_store_visualization_radio(selected_data: List[str]) -> List[str]:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_STATISTICS_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def _update_store_stastics_options(selected_data: List[str]) -> List[str]:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.PLOT_FANCHART_OPTIONS_CHECKLIST
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_FANCHART_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def _update_store_fanchart_options(selected_data: List[str]) -> List[str]:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.PLOT_TRACE_OPTIONS_CHECKLIST),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.PLOT_TRACE_OPTIONS_CHECKLIST
                ).to_string(),
                "value",
            ),
        )
        def _update_store_trace_options(selected_data: List[str]) -> List[str]:
            return selected_data
