import datetime
from typing import Dict, List, Set, Tuple, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import ALL, Input, Output, State, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import WellOverviewFigure, format_well_overview_figure
from .._plugin_ids import PluginIds
from .._types import ChartType
from .._view_elements import Graph
from ._settings import OverviewFilter, OverviewPlotSettings


class OverviewView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        BAR_CHART = "bar-chart"
        PLOT_SETTINGS = "plot-settings"
        FILTER = "filter"
        MAIN_COLUMN = "main-column"
        GRAPH = "graph"
        FIGURE = "figure"

    def __init__(
        self,
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well overview")

        self.data_models = data_models
        self.theme = theme
        self.wells: List[str] = []
        self.well_attr: dict = {}
        for _, ens_data_model in data_models.items():
            self.wells.extend(
                [well for well in ens_data_model.wells if well not in self.wells]
            )
            for category, values in ens_data_model.well_attributes.items():
                if category not in self.well_attr:
                    self.well_attr[category] = values
                else:
                    self.well_attr[category].extend(
                        [
                            value
                            for value in values
                            if value not in self.well_attr[category]
                        ]
                    )

        self.add_settings_group(
            OverviewPlotSettings(self.data_models), OverviewView.Ids.PLOT_SETTINGS
        )
        self.add_settings_group(
            OverviewFilter(self.data_models), OverviewView.Ids.FILTER
        )

        self.main_column = self.add_column(OverviewView.Ids.MAIN_COLUMN)

        self.main_column.add_view_element(Graph(), OverviewView.Ids.GRAPH)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(OverviewView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Output(self.get_store_unique_id(PluginIds.Stores.CURRENT_FIG), "value"),
            Output(self.get_store_unique_id(PluginIds.Stores.PREV_PLOT_TYPE), "value"),
            Input(
                self.settings_group(OverviewView.Ids.PLOT_SETTINGS)
                .component_unique_id(OverviewPlotSettings.Ids.SELECTED_ENSEMBLES)
                .to_string(),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_PLOT_LAYOUT),
                "value",
            ),
            Input(
                self.settings_group(OverviewView.Ids.PLOT_SETTINGS)
                .component_unique_id(OverviewPlotSettings.Ids.SELECTED_RESPONSE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(OverviewView.Ids.PLOT_SETTINGS)
                .component_unique_id(
                    OverviewPlotSettings.Ids.ONLY_PRODUCTION_AFTER_DATE
                )
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(OverviewView.Ids.PLOT_SETTINGS)
                .component_unique_id(OverviewPlotSettings.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELL_ATTR),
                "value",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.CURRENT_FIG), "value"),
            State(self.get_store_unique_id(PluginIds.Stores.PREV_PLOT_TYPE), "value"),
        )
        def _update_graph(
            ensembles: List[str],
            checklist_values: List[str],
            sumvec: str,
            prod_after_date: Union[str, None],
            chart_selected: ChartType,
            wells_selected: List[str],
            well_attr_selected: List[str],
            current_fig_dict: dict,
            prev_plot: ChartType,
        ) -> Tuple[List[Component], dict, ChartType]:
            # pylint: disable=too-many-locals
            # pylint: disable=too-many-arguments

            """Updates the well overview graph with selected input (f.ex chart type)"""
            ctx = callback_context.triggered[0]["prop_id"]
            settings = checklist_values
            layout_trigger = False

            if "plot-layout" in ctx and chart_selected == prev_plot:
                layout_trigger = True

            if well_attr_selected:
                well_attributes_selected: Dict[str, List[str]] = {}
                for category, value in self.well_attr.items():
                    attr_list = []
                    for attr_l in well_attr_selected:
                        for attr in attr_l:
                            if attr in value:
                                attr_list.append(attr)
                    well_attributes_selected[category] = attr_list

            # Make set of wells that match the well_attributes
            # Well attributes that does not exist in one ensemble will be ignored
            wellattr_filtered_wells: Set[str] = set()
            for _, ens_data_model in self.data_models.items():
                wellattr_filtered_wells = wellattr_filtered_wells.union(
                    ens_data_model.filter_on_well_attributes(well_attributes_selected)
                )

            # Take the intersection with wells_selected.
            # this way preserves the order in wells_selected and will not have duplicates
            filtered_wells = [
                well for well in wells_selected if well in wellattr_filtered_wells
            ]

            # If the event is a plot settings event, then we only update the formatting
            # and not the figure data
            chart_selected_type = ChartType(chart_selected)
            if current_fig_dict is not None and layout_trigger:
                fig_dict = format_well_overview_figure(
                    go.Figure(current_fig_dict),
                    chart_selected_type,
                    settings,
                    sumvec,
                    prod_after_date,
                )
            else:
                figure = WellOverviewFigure(
                    ensembles,
                    self.data_models,
                    sumvec,
                    datetime.datetime.strptime(prod_after_date, "%Y-%m-%d")
                    if prod_after_date is not None
                    else None,
                    chart_selected_type,
                    filtered_wells,
                    self.theme,
                )

                fig_dict = format_well_overview_figure(
                    figure.figure,
                    chart_selected_type,
                    settings,
                    sumvec,
                    prod_after_date,
                )

            return (
                [
                    wcc.Graph(
                        id=self.unique_id(OverviewView.Ids.FIGURE),
                        style={"height": "87vh"},
                        figure=fig_dict,
                    )
                ],
                fig_dict,
                chart_selected,
            )
