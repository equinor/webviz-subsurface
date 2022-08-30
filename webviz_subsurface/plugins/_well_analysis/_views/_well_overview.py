import datetime
from typing import Dict, List, Set, Tuple, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import ALL, Input, Output, State, callback, callback_context, html
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import WellOverviewFigure, format_well_overview_figure
from .._plugin_ids import PluginIds
from .._types import ChartType


class WellOverviewSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        # chart controls
        CHARTTYPE = "charttype"
        SELECTED_ENSEMBLES = "selected-ensembles"
        SELECTED_RESPONSE = "selected-response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"

        # chart layout
        CHARTTYPE_SETTINGS = "charttype-settings"
        CHARTTYPE_CHECKLIST = "charttype-checklist"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Settings")

        self.ensembles = list(data_models.keys())
        self.dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            self.dates = self.dates.union(ens_data_model.dates)
        self.sorted_dates: List[datetime.datetime] = sorted(list(self.dates))

    def layout(self) -> List[Component]:
        settings_id = self.register_component_unique_id(
            WellOverviewSettings.Ids.CHARTTYPE_SETTINGS
        )
        checklist_id = self.register_component_unique_id(
            WellOverviewSettings.Ids.CHARTTYPE_CHECKLIST
        )
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    WellOverviewSettings.Ids.CHARTTYPE
                ),
                label="Chart type",
                options=[
                    {"label": "Bar chart", "value": ChartType.BAR},
                    {"label": "Pie chart", "value": ChartType.PIE},
                    {"label": "Stacked area chart", "value": ChartType.AREA},
                ],
                value=ChartType.BAR,
                vertical=True,
            ),
            wcc.Dropdown(
                label="Ensembles",
                id=self.register_component_unique_id(
                    WellOverviewSettings.Ids.SELECTED_ENSEMBLES
                ),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(
                    WellOverviewSettings.Ids.SELECTED_RESPONSE
                ),
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
                id=self.register_component_unique_id(
                    WellOverviewSettings.Ids.ONLY_PRODUCTION_AFTER_DATE
                ),
                options=[
                    {
                        "label": dte.strftime("%Y-%m-%d"),
                        "value": dte.strftime("%Y-%m-%d"),
                    }
                    for dte in self.sorted_dates
                ],
                multi=False,
            ),
            html.Div(
                children=[
                    html.Div(
                        id={"id": settings_id, "charttype": "bar"},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": "bar"},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {"label": "Overlay bars", "value": "overlay_bars"},
                                {
                                    "label": "Show prod as text",
                                    "value": "show_prod_text",
                                },
                                {
                                    "label": "White background",
                                    "value": "white_background",
                                },
                            ],
                            value=["legend"],
                        ),
                    ),
                    html.Div(
                        id={"id": settings_id, "charttype": "pie"},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": "pie"},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {
                                    "label": "Show prod as text",
                                    "value": "show_prod_text",
                                },
                            ],
                            value=[],
                        ),
                    ),
                    html.Div(
                        id={"id": settings_id, "charttype": "area"},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": "area"},
                            options=[
                                {"label": "Show legend", "value": "legend"},
                                {
                                    "label": "White background",
                                    "value": "white_background",
                                },
                            ],
                            value=["legend"],
                        ),
                    ),
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                {
                    "id": self.component_unique_id(
                        WellOverviewSettings.Ids.CHARTTYPE_SETTINGS
                    ).to_string(),
                    "charttype": ALL,
                },
                "style",
            ),
            Input(
                self.component_unique_id(
                    WellOverviewSettings.Ids.CHARTTYPE
                ).to_string(),
                "value",
            ),
            State(
                {
                    "id": self.component_unique_id(
                        WellOverviewSettings.Ids.CHARTTYPE_SETTINGS
                    ).to_string(),
                    "charttype": ALL,
                },
                "id",
            ),
        )
        def _display_charttype_settings(
            chart_selected: str, charttype_settings_ids: list
        ) -> list:
            """Display only the settings relevant for the currently selected chart type."""
            return [
                {"display": "block"}
                if settings_id["charttype"] == chart_selected
                else {"display": "none"}
                for settings_id in charttype_settings_ids
            ]


class WellOverviewFilters(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        # filters
        SELECTED_WELLS = "selected-wells"
        SELECTED_WELL_ATTR = "selected-well-attr"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Filters")
        self.wells: List[str] = []
        self.well_attr: dict = {}
        for ens_data_model in data_models.values():
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

    def layout(self) -> List[Component]:
        self.register_component_unique_id(WellOverviewFilters.Ids.SELECTED_WELL_ATTR)
        return [
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(self.wells)),
                id=self.register_component_unique_id(
                    WellOverviewFilters.Ids.SELECTED_WELLS
                ),
                options=[{"label": well, "value": well} for well in self.wells],
                value=self.wells,
                multi=True,
            )
        ] + [
            # Adding well attributes selectors
            wcc.SelectWithLabel(
                label=category.capitalize(),
                size=min(5, len(values)),
                id={
                    "id": self.component_unique_id(
                        WellOverviewFilters.Ids.SELECTED_WELL_ATTR
                    ).to_string(),
                    "category": category,
                },
                options=[{"label": value, "value": value} for value in values],
                value=values,
                multi=True,
            )
            for category, values in self.well_attr.items()
        ]


class WellOverviewView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        SETTINGS = "settings"
        FILTERS = "filters"
        MAIN_COLUMN = "main-column"
        CURRENT_FIGURE = "current-figure"
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
            WellOverviewSettings(self.data_models), self.Ids.SETTINGS
        )
        self.add_settings_group(WellOverviewFilters(self.data_models), self.Ids.FILTERS)

        self.main_column = self.add_column(self.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(self.Ids.MAIN_COLUMN).get_unique_id().to_string(),
                "children",
            ),
            Output(
                self.get_store_unique_id(PluginIds.Stores.CURRENT_FIGURE),
                "value",
            ),
            Output(
                self.get_store_unique_id(PluginIds.Stores.PREV_PLOT_TYPE),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.SELECTED_ENSEMBLES)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": self.settings_group(self.Ids.SETTINGS)
                    .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE_CHECKLIST)
                    .to_string(),
                    "charttype": ALL,
                },
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.SELECTED_RESPONSE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(
                    WellOverviewSettings.Ids.ONLY_PRODUCTION_AFTER_DATE
                )
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(WellOverviewFilters.Ids.SELECTED_WELLS)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": self.settings_group(self.Ids.FILTERS)
                    .component_unique_id(WellOverviewFilters.Ids.SELECTED_WELL_ATTR)
                    .to_string(),
                    "category": ALL,
                },
                "value",
            ),
            State(self.get_store_unique_id(PluginIds.Stores.CURRENT_FIGURE), "value"),
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
        ) -> Tuple[Component, dict, ChartType]:
            # pylint: disable=too-many-locals
            # pylint: disable=too-many-arguments
            """Updates the well overview graph with selected input (f.ex chart type)"""
            if not ensembles:
                return "No ensembles selected", current_fig_dict, prev_plot

            ctx = callback_context.triggered[0]["prop_id"]
            settings = checklist_values
            layout_trigger = False

            if "plot-layout" in ctx and chart_selected == prev_plot:
                layout_trigger = True

            well_attributes_selected: Dict[str, List[str]] = {}
            if well_attr_selected:
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
            for ens_data_model in self.data_models.values():
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
                        id=self.unique_id(self.Ids.FIGURE),
                        style={"height": "87vh"},
                        figure=fig_dict,
                    )
                ],
                fig_dict,
                chart_selected,
            )
