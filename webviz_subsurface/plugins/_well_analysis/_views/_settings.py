import datetime
from typing import Callable, Dict, List, Set

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._types import ChartType


class OverviewPlotSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        #plot controls
        PLOT_TYPE = "plot-type"
        SELECTED_ENSEMBLES = "selected_ensembles"
        SELECTED_RESPONSE = "selected-response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"

        #filters
        SLECTED_WELLS = "selected-wells"
        SELECTED_WELLTYPE = "selected-welltype"

        #plot layout
        CHECKBOX = "checkbox"
        PLOT_LAYOUT = "plot-layout"

        

    def __init__(self,
        data_models: Dict[str, EnsembleWellAnalysisData]
    ) -> None:

        super().__init__("Plot Settings")

        self.plot_layout_id = self.register_component_unique_id(OverviewPlotSettings.Ids.PLOT_LAYOUT)

        self.ensembles = list(data_models.keys())
        self.dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            self.dates = self.dates.union(ens_data_model.dates)
        self.sorted_dates: List[datetime.datetime] = sorted(list(self.dates))


    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.PLOT_TYPE),
                label="Plot type",
                options=[
                    {"label": "Bar chart", "value": "bar-chart"},
                    {"label": "Pie chart", "value": "pie-chart"},
                    {"label": "Stacked area chart", "value": "stacked-chart"},
                ],
                value="bar-chart",
                vertical=True,
            ),
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.SELECTED_ENSEMBLES),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.SELECTED_RESPONSE),
                options=[
                    {"label": "Oil production", "value": "WOPT"},
                    {"label": "Gas production", "value": "WGPT"},
                    {"label": "Water production", "value": "WWPT"},
                ],
                value="WOPT",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Only Production after date",
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.ONLY_PRODUCTION_AFTER_DATE),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self.sorted_dates
                ],
                multi=False,
            ),
             wcc.FlexBox(
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.CHECKBOX),
                children=[
                    wcc.Checklist(
                        id=self.plot_layout_id ,
                        options=[
                            {"label": "Show legend", "value": "legend"},
                            {"label": "Overlay bars", "value": "overlay_bars"},
                            {"label": "Show prod as text", "value": "show_prod_text"},
                            {"label": "White background", "value": "white_background"},
                        ],
                        value=["legend"],
                        
                    )
                ],
            ),

        ]
    
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(OverviewPlotSettings.Ids.CHECKBOX).to_string(), "children"
            ),
            Input(self.component_unique_id(OverviewPlotSettings.Ids.PLOT_TYPE).to_string(), "value"),
        )
        def _update_checkbox(selected_plot: str) -> List[Component]:
            box_list = []
            if selected_plot == "bar-chart":
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id ,
                        options=[
                            {"label": "Show legend", "value": "legend"},
                            {"label": "Overlay bars", "value": "overlay_bars"},
                            {"label": "Show prod as text", "value": "show_prod_text"},
                            {"label": "White background", "value": "white_background"},
                        ],
                        value=["legend"],
                        
                    )
                ]
            if selected_plot == "pie-chart":
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id ,
                        options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "Show prod as text", "value": "show_prod_text"},
                    ],
                    value=[],
                        
                    )
                ]
            if selected_plot == "stacked-chart":
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id ,
                        options=[
                        {"label": "Show legend", "value": "legend"},
                        {"label": "White background", "value": "white_background"},
                    ],
                    value=["legend"],
                        
                    )
                ]
            return box_list



class OverviewFilter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        #filters
        SLECTED_WELLS = "selected-wells"
        SELECTED_WELL_ATTR = "selected-welltype"
        

    def __init__(self,
        data_models: Dict[str, EnsembleWellAnalysisData]
    ) -> None:

        super().__init__("Filter")
        self.wells = []
        self.well_attr = {}
        for _, ens_data_model in data_models.items():
            self.wells.extend([well for well in ens_data_model.wells if well not in self.wells])
            for category, values in ens_data_model.well_attributes.items():
                if category not in self.well_attr:
                    self.well_attr[category] = values
                else:
                    self.well_attr[category].extend(
                        [value for value in values if value not in self.well_attr[category]]
                    )



    def layout(self) -> List[Component]:
        return ([
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(self.wells)),
                id=self.register_component_unique_id(OverviewFilter.Ids.SLECTED_WELLS),
                options=[{"label": well, "value": well} for well in self.wells],
                value=self.wells,
                multi=True,
            )
        ]
        # Adding well attributes selectors
        + [
            wcc.SelectWithLabel(
                label=category.capitalize(),
                size=min(5, len(values)),
                id={
                    "id": self.register_component_unique_id(OverviewFilter.Ids.SELECTED_WELL_ATTR),
                    "category": category,
                },
                options=[{"label": value, "value": value} for value in values],
                value=values,
                multi=True,
            )
            for category, values in self.well_attr.items()
        ])


