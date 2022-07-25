from typing import Dict, List

import webviz_core_components as wcc
from dash import ALL, Input, Output, callback
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import create_well_control_figure
from .._plugin_ids import PluginIds
from .._types import PressurePlotMode
from ._settings import ControlPressureOptions, ControlSettings


class ControlView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        BAR_CHART = "bar-chart"
        PLOT_SETTINGS = "plot-settings"
        CONTROL_OPTIONS = "control-options"
        FILTER = "filter"
        MAIN_COLUMN = "main-column"
        GRAPH = "graph"

    def __init__(
        self,
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well Control")

        self.data_models = data_models
        self.theme = theme

        self.add_settings_group(
            ControlSettings(self.data_models), ControlView.Ids.PLOT_SETTINGS
        )
        self.add_settings_group(
            ControlPressureOptions(self.data_models), ControlView.Ids.CONTROL_OPTIONS
        )

        self.main_column = self.add_column(ControlView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(ControlView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(ControlView.Ids.PLOT_SETTINGS)
                .component_unique_id(ControlSettings.Ids.SELECTED_ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ControlView.Ids.PLOT_SETTINGS)
                .component_unique_id(ControlSettings.Ids.SELECTED_WELL)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ControlView.Ids.CONTROL_OPTIONS)
                .component_unique_id(ControlPressureOptions.Ids.INCLUDE_BHP)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ControlView.Ids.CONTROL_OPTIONS)
                .component_unique_id(ControlPressureOptions.Ids.MEAN_OR_REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_REALIZATION),
                "value",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.DISPLAY_CTRL_MODE_BAR),
                "value",
            ),
            Input(
                self.settings_group(ControlView.Ids.PLOT_SETTINGS)
                .component_unique_id(ControlSettings.Ids.SHARED_X_AXIS)
                .to_string(),
                "value",
            ),
        )
        def _update_graph(
            ensemble: str,
            well: str,
            include_bhp: List[str],
            pressure_plot_mode_string: str,
            real: int,
            display_ctrlmode_bar: bool,
            shared_xaxes: List[str],
        ) -> List[Component]:
            """Updates the well control figure"""
            pressure_plot_mode = PressurePlotMode(pressure_plot_mode_string)
            fig = create_well_control_figure(
                self.data_models[ensemble].get_node_info(
                    well, pressure_plot_mode, real
                ),
                self.data_models[ensemble].summary_data,
                pressure_plot_mode,
                real,
                display_ctrlmode_bar,
                "shared_xaxes" in shared_xaxes,
                "include_bhp" in include_bhp,
                self.theme,
            )

            return wcc.Graph(style={"height": "87vh"}, figure=fig)
