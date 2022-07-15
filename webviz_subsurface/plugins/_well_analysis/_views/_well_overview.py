import datetime
from typing import Dict, List, Set, Tuple, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import Input, Output, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_wlf_tutorial.plugins.population_analysis.views import population

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import WellOverviewFigure, format_well_overview_figure
from .._plugin_ids import PluginIds
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


    def __init__(self, 
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well overview")

        self.data_models = data_models
        self.theme = theme

        self.add_settings_group(OverviewPlotSettings(self.data_models), OverviewView.Ids.PLOT_SETTINGS)
        self.add_settings_group(OverviewFilter(self.data_models), OverviewView.Ids.FILTER)

        self.main_column = self.add_column(OverviewView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(OverviewView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(OverviewView.Ids.PLOT_SETTINGS)
                .component_unique_id(OverviewPlotSettings.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
        )
        def _update_graph(
            ensembles: List[str],
            checklist_values: List[List[str]],
            sumvec: str,
            prod_after_date: Union[str, None],
            chart_selected: str,
            wells_selected: List[str],
            well_attr_selected: List[str],
            checklist_ids: List[Dict[str, str]],
            well_attr_ids: List[Dict[str, str]],
            current_fig_dict: dict,
        ) -> List[Component]:
            # pylint: disable=too-many-locals
            # pylint: disable=too-many-arguments

            """Updates the well overview graph with selected input (f.ex chart type)"""

            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]

            settings = {
                checklist_id["charttype"]: checklist_values[i]
                for i, checklist_id in enumerate(checklist_ids)
            }
            well_attributes_selected: Dict[str, List[str]] = {
                well_attr_id["category"]: list(well_attr_selected[i])
                for i, well_attr_id in enumerate(well_attr_ids)
            }

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
            if current_fig_dict is not None and is_plot_settings_event(ctx, get_uuid):
                fig_dict = format_well_overview_figure(
                    go.Figure(current_fig_dict),
                    chart_selected,
                    settings[chart_selected_type.value],
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
                    self.themetheme,
                )

                fig_dict = format_well_overview_figure(
                    figure.figure,
                    chart_selected_type,
                    settings[chart_selected_type.value],
                    sumvec,
                    prod_after_date,
                )

            return [
                wcc.Graph(
                    id=self.unique_id(OverviewView.Ids.GRAPH),
                    style={"height": "87vh"},
                    figure=fig_dict,
                )
            ]


