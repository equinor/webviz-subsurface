import datetime
from typing import Callable, Dict, List, Set

import webviz_core_components as wcc
from dash import ALL, Input, Output, State, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._plugin_ids import PluginIds
from .._types import ChartType


class OverviewPlotSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        # plot controls
        PLOT_TYPE = "plot-type"
        SELECTED_ENSEMBLES = "selected_ensembles"
        SELECTED_RESPONSE = "selected-response"
        ONLY_PRODUCTION_AFTER_DATE = "only-production-after-date"

        # plot layout
        CHECKBOX = "checkbox"
        PLOT_LAYOUT = "plot-layout"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Plot Settings")

        self.plot_layout_id = self.register_component_unique_id(
            OverviewPlotSettings.Ids.PLOT_LAYOUT
        )

        self.ensembles = list(data_models.keys())
        self.dates: Set[datetime.datetime] = set()
        for _, ens_data_model in data_models.items():
            self.dates = self.dates.union(ens_data_model.dates)
        self.sorted_dates: List[datetime.datetime] = sorted(list(self.dates))

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(
                    OverviewPlotSettings.Ids.PLOT_TYPE
                ),
                label="Plot type",
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
                    OverviewPlotSettings.Ids.SELECTED_ENSEMBLES
                ),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            wcc.Dropdown(
                label="Response",
                id=self.register_component_unique_id(
                    OverviewPlotSettings.Ids.SELECTED_RESPONSE
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
                    OverviewPlotSettings.Ids.ONLY_PRODUCTION_AFTER_DATE
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
            wcc.FlexBox(
                id=self.register_component_unique_id(OverviewPlotSettings.Ids.CHECKBOX),
                children=[
                    wcc.Checklist(
                        id={"id": self.plot_layout_id, "charttype": "bar"},
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
                self.component_unique_id(OverviewPlotSettings.Ids.CHECKBOX).to_string(),
                "children",
            ),
            Input(
                self.component_unique_id(
                    OverviewPlotSettings.Ids.PLOT_TYPE
                ).to_string(),
                "value",
            ),
        )
        def _update_checkbox(selected_plot: str) -> List[Component]:
            box_list = []
            if selected_plot == ChartType.BAR:
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id,
                        options=[
                            {"label": "Show legend", "value": "legend"},
                            {"label": "Overlay bars", "value": "overlay_bars"},
                            {"label": "Show prod as text", "value": "show_prod_text"},
                            {"label": "White background", "value": "white_background"},
                        ],
                        value=["legend"],
                    )
                ]
            if selected_plot == ChartType.PIE:
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id,
                        options=[
                            {"label": "Show legend", "value": "legend"},
                            {"label": "Show prod as text", "value": "show_prod_text"},
                        ],
                        value=[],
                    )
                ]
            if selected_plot == ChartType.AREA:
                box_list = [
                    wcc.Checklist(
                        id=self.plot_layout_id,
                        options=[
                            {"label": "Show legend", "value": "legend"},
                            {"label": "White background", "value": "white_background"},
                        ],
                        value=["legend"],
                    )
                ]
            return box_list

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_PLOT_LAYOUT), "value"
            ),
            Input(self.plot_layout_id, "value"),
        )
        def _set_plot_layout(settings: List[str]) -> List[str]:
            return settings


class OverviewFilter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        # filters
        SLECTED_WELLS = "selected-wells"
        SELECTED_WELL_ATTR = "selected-welltype"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Filter")
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

    def layout(self) -> List[Component]:
        return (
            [
                wcc.SelectWithLabel(
                    label="Well",
                    size=min(10, len(self.wells)),
                    id=self.register_component_unique_id(
                        OverviewFilter.Ids.SLECTED_WELLS
                    ),
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
                        "id": self.register_component_unique_id(
                            OverviewFilter.Ids.SELECTED_WELL_ATTR
                        ),
                        "category": category,
                    },
                    options=[{"label": value, "value": value} for value in values],
                    value=values,
                    multi=True,
                )
                for category, values in self.well_attr.items()
            ]
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "value"),
            Input(
                self.component_unique_id(OverviewFilter.Ids.SLECTED_WELLS).to_string(),
                "value",
            ),
        )
        def _set_wells(wells: List[str]) -> List[str]:
            return wells

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELL_ATTR), "value"
            ),
            Input(
                {
                    "id": self.component_unique_id(
                        OverviewFilter.Ids.SELECTED_WELL_ATTR
                    ).to_string(),
                    "category": ALL,
                },
                "value",
            ),
        )
        def _set_well_attr(well_attr: List[str]) -> List[str]:
            return well_attr


class ControlSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        SELECTED_ENSEMBLE = "selected-ensemble"
        SELECTED_WELL = "selected-well"
        SHARED_X_AXIS = "shared-x-axis"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Plot Controls")
        self.ensembles = list(data_models.keys())

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(
                    ControlSettings.Ids.SELECTED_ENSEMBLE
                ),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles[0],
                multi=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=self.register_component_unique_id(ControlSettings.Ids.SELECTED_WELL),
                options=[],
                value=None,
                multi=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(ControlSettings.Ids.SHARED_X_AXIS),
                options=[{"label": "Shared x-axis", "value": "shared_xaxes"}],
                value=["shared_xaxes"],
            ),
        ]


class ControlPressureOptions(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        INCLUDE_BHP = "include-bhp"
        MEAN_OR_REALIZATION = "mean-or-realization"
        SELECTED_REALIZATION = "selected-realization"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Plot Controls")
        self.ensembles = list(data_models.keys())

    def layout(self) -> List[Component]:
        return []
