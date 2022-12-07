import datetime
from typing import Any, Dict, List, Optional, Union

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._types import ChartType
from ..._utils import EnsembleWellAnalysisData
from ._settings import (
    WellOverviewChartType,
    WellOverviewFilters,
    WellOverviewLayoutOptions,
    WellOverviewSelections,
)
from ._utils import WellOverviewFigure, format_well_overview_figure
from ._view_element import WellOverviewViewElement


class WellOverviewView(ViewABC):
    class Ids(StrEnum):
        CHART_TYPE = "chart-type"
        SELECTIONS = "selections"
        LAYOUT_OPTIONS = "layout-options"
        FILTERS = "filters"
        CURRENT_FIGURE = "current-figure"
        VIEW_ELEMENT = "view-element"

    def __init__(
        self,
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well overview")

        self._data_models = data_models
        self._theme = theme

        self.add_settings_groups(
            {
                self.Ids.CHART_TYPE: WellOverviewChartType(),
                self.Ids.SELECTIONS: WellOverviewSelections(self._data_models),
                self.Ids.LAYOUT_OPTIONS: WellOverviewLayoutOptions(),
                self.Ids.FILTERS: WellOverviewFilters(self._data_models),
            }
        )

        main_column = self.add_column()
        main_column.add_view_element(WellOverviewViewElement(), self.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.LAYOUT_OPTIONS,
                        WellOverviewLayoutOptions.Ids.CHARTTYPE_SETTINGS,
                    ),
                    "charttype": ALL,
                },
                "style",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.CHART_TYPE, WellOverviewChartType.Ids.CHARTTYPE
                ),
                "value",
            ),
            State(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.LAYOUT_OPTIONS,
                        WellOverviewLayoutOptions.Ids.CHARTTYPE_SETTINGS,
                    ),
                    "charttype": ALL,
                },
                "id",
            ),
        )
        @callback_typecheck
        def _display_charttype_settings(
            chart_selected: ChartType, charttype_settings_ids: list
        ) -> list:
            """Display only the settings relevant for the currently selected chart type."""
            return [
                {"display": "block"}
                if settings_id["charttype"] == chart_selected
                else {"display": "none"}
                for settings_id in charttype_settings_ids
            ]

        @callback(
            Output(
                self.view_element(self.Ids.VIEW_ELEMENT)
                .component_unique_id(WellOverviewViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, WellOverviewSelections.Ids.ENSEMBLES
                ),
                "value",
            ),
            Input(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.LAYOUT_OPTIONS,
                        WellOverviewLayoutOptions.Ids.CHARTTYPE_CHECKLIST,
                    ),
                    "charttype": ALL,
                },
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, WellOverviewSelections.Ids.RESPONSE
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS,
                    WellOverviewSelections.Ids.ONLY_PRODUCTION_AFTER_DATE,
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.CHART_TYPE, WellOverviewChartType.Ids.CHARTTYPE
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.FILTERS, WellOverviewFilters.Ids.SELECTED_WELLS
                ),
                "value",
            ),
            State(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.LAYOUT_OPTIONS,
                        WellOverviewLayoutOptions.Ids.CHARTTYPE_CHECKLIST,
                    ),
                    "charttype": ALL,
                },
                "id",
            ),
            State(
                self.view_element(self.Ids.VIEW_ELEMENT)
                .component_unique_id(WellOverviewViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
        )
        @callback_typecheck
        def _update_graph(
            ensembles: List[str],
            checklist_values: List[List[str]],
            sumvec: str,
            prod_after_date: Union[str, None],
            charttype_selected: ChartType,
            wells_selected: List[str],
            checklist_ids: List[Dict[str, str]],
            current_fig_dict: Optional[Dict[str, Any]],
        ) -> Component:
            """Updates the well overview graph with selected input (f.ex chart type)"""
            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]

            settings = {
                checklist_id["charttype"]: checklist_values[i]
                for i, checklist_id in enumerate(checklist_ids)
            }

            # If the event is a plot settings event, then we only update the formatting
            # and not the figure data
            if (
                current_fig_dict is not None
                and self.settings_group(self.Ids.LAYOUT_OPTIONS)
                .component_unique_id(WellOverviewLayoutOptions.Ids.CHARTTYPE_CHECKLIST)
                .to_string()
                in ctx
            ):
                fig_dict = format_well_overview_figure(
                    go.Figure(current_fig_dict),
                    charttype_selected,
                    settings[charttype_selected],
                    sumvec,
                    prod_after_date,
                )
            else:
                figure = WellOverviewFigure(
                    ensembles,
                    self._data_models,
                    sumvec,
                    datetime.datetime.strptime(prod_after_date, "%Y-%m-%d")
                    if prod_after_date is not None
                    else None,
                    charttype_selected,
                    wells_selected,
                    self._theme,
                )

                fig_dict = format_well_overview_figure(
                    figure.figure,
                    charttype_selected,
                    settings[charttype_selected],
                    sumvec,
                    prod_after_date,
                )

            return fig_dict
