import datetime
from typing import Any, Dict, List, Optional, Set, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import ALL, Input, Output, State, callback, callback_context, html
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from ..._types import ChartType
from ..._utils import EnsembleWellAnalysisData
from ._utils import WellOverviewFigure, format_well_overview_figure
from ._view_element import WellOverviewViewElement


class WellOverviewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        CHARTTYPE = "charttype"
        ENSEMBLES = "ensembles"
        RESPONSE = "response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"
        CHARTTYPE_SETTINGS = "charttype-settings"
        CHARTTYPE_CHECKLIST = "charttype-checklist"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:
        super().__init__("Settings")

        self._ensembles = list(data_models.keys())

        dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            dates = dates.union(ens_data_model.dates)
        self._sorted_dates: List[datetime.datetime] = sorted(list(dates))

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
                    WellOverviewSettings.Ids.ENSEMBLES
                ),
                options=[{"label": col, "value": col} for col in self._ensembles],
                value=self._ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(WellOverviewSettings.Ids.RESPONSE),
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
                    for dte in self._sorted_dates
                ],
                multi=False,
            ),
            html.Div(
                children=[
                    html.Div(
                        id={"id": settings_id, "charttype": ChartType.BAR},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.BAR},
                            label="Layout options",
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
                        id={"id": settings_id, "charttype": ChartType.PIE},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.PIE},
                            label="Layout options",
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
                        id={"id": settings_id, "charttype": ChartType.AREA},
                        children=wcc.Checklist(
                            id={"id": checklist_id, "charttype": ChartType.AREA},
                            label="Layout options",
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


class WellOverviewFilters(SettingsGroupABC):
    class Ids(StrEnum):
        SELECTED_WELLS = "selected-wells"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:
        super().__init__("Filters")
        self._wells: List[str] = []
        for ens_data_model in data_models.values():
            self._wells.extend(
                [well for well in ens_data_model.wells if well not in self._wells]
            )

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Well",
                size=min(10, len(self._wells)),
                id=self.register_component_unique_id(
                    WellOverviewFilters.Ids.SELECTED_WELLS
                ),
                options=[{"label": well, "value": well} for well in self._wells],
                value=self._wells,
                multi=True,
            )
        ]


class WellOverviewView(ViewABC):
    class Ids(StrEnum):
        SETTINGS = "settings"
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

        self.add_settings_group(
            WellOverviewSettings(self._data_models), self.Ids.SETTINGS
        )
        self.add_settings_group(
            WellOverviewFilters(self._data_models), self.Ids.FILTERS
        )
        main_column = self.add_column()
        main_column.add_view_element(WellOverviewViewElement(), self.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(self.Ids.VIEW_ELEMENT)
                .component_unique_id(WellOverviewViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.ENSEMBLES)
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
                .component_unique_id(WellOverviewSettings.Ids.RESPONSE)
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
            State(
                {
                    "id": self.settings_group(self.Ids.SETTINGS)
                    .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE_CHECKLIST)
                    .to_string(),
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
                and self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE_CHECKLIST)
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
