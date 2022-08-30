from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback, html
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._figures import create_well_control_figure
from .._types import PressurePlotMode


class WellControlSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        ENSEMBLE = "ensemble"
        WELL = "well"
        SHARED_X_AXIS = "shared-x-axis"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Plot Controls")
        self.ensembles = list(data_models.keys())
        self.wells: List[str] = []
        for _, ens_data_model in data_models.items():
            self.wells.extend(
                [well for well in ens_data_model.wells if well not in self.wells]
            )

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(WellControlSettings.Ids.ENSEMBLE),
                options=[{"label": col, "value": col} for col in self.ensembles],
                value=self.ensembles[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=self.register_component_unique_id(WellControlSettings.Ids.WELL),
                options=[{"label": well, "value": well} for well in self.wells],
                value=self.wells[0],
                multi=False,
                clearable=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(
                    WellControlSettings.Ids.SHARED_X_AXIS
                ),
                options=[{"label": "Shared x-axis", "value": "shared_xaxes"}],
                value=["shared_xaxes"],
            ),
        ]


class WellControlPressurePlotOptions(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        INCLUDE_BHP = "include-bhp"
        PRESSURE_PLOT_MODE = "pressure-plot-mode"
        REALIZATION_BOX = "realization-box"
        REALIZATION = "realization"
        DISPLAY_CTRL_MODE_BAR = "display-ctrl-mode-bar"

    def __init__(self, data_models: Dict[str, EnsembleWellAnalysisData]) -> None:

        super().__init__("Pressure Plot Options")
        self.data_models = data_models
        self.ensembles = list(data_models.keys())

    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                id=self.register_component_unique_id(
                    WellControlPressurePlotOptions.Ids.INCLUDE_BHP
                ),
                options=[{"label": "Include BHP", "value": "include_bhp"}],
                value=["include_bhp"],
            ),
            wcc.RadioItems(
                label="Mean or realization",
                id=self.register_component_unique_id(
                    WellControlPressurePlotOptions.Ids.PRESSURE_PLOT_MODE
                ),
                options=[
                    {
                        "label": "Mean of producing real.",
                        "value": PressurePlotMode.MEAN.value,
                    },
                    {
                        "label": "Single realization",
                        "value": PressurePlotMode.SINGLE_REAL.value,
                    },
                ],
                value=PressurePlotMode.MEAN.value,
            ),
            html.Div(
                id=self.register_component_unique_id(
                    WellControlPressurePlotOptions.Ids.REALIZATION_BOX
                ),
                children=[
                    wcc.Dropdown(
                        id=self.register_component_unique_id(
                            WellControlPressurePlotOptions.Ids.REALIZATION
                        ),
                        options=[],
                        value=None,
                        multi=False,
                    ),
                    wcc.Checklist(
                        id=self.register_component_unique_id(
                            WellControlPressurePlotOptions.Ids.DISPLAY_CTRL_MODE_BAR
                        ),
                        options=[
                            {
                                "label": "Display ctrl mode bar",
                                "value": "ctrlmode_bar",
                            }
                        ],
                        value=["ctrlmode_bar"],
                    ),
                ],
            ),
        ]


class WellControlView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        SETTINGS = "settings"
        PRESSUREPLOT_OPTIONS = "pressure-plot-options"
        MAIN_COLUMN = "main-column"

    def __init__(
        self,
        data_models: Dict[str, EnsembleWellAnalysisData],
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Well Control")

        self.data_models = data_models
        self.theme = theme

        self.add_settings_group(
            WellControlSettings(self.data_models), WellControlView.Ids.SETTINGS
        )
        self.add_settings_group(
            WellControlPressurePlotOptions(self.data_models),
            WellControlView.Ids.PRESSUREPLOT_OPTIONS,
        )

        self.main_column = self.add_column(WellControlView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.WELL)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.REALIZATION)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
        )
        def _update_dropdowns(
            ensemble: str, state_well: str, state_real: int
        ) -> Tuple[
            List[Dict[str, str]], Optional[str], List[Dict[str, Any]], Optional[int]
        ]:
            """Updates the well and realization dropdowns with ensemble values"""
            wells = self.data_models[ensemble].wells
            reals = self.data_models[ensemble].realizations
            return (
                [{"label": well, "value": well} for well in wells],
                state_well if state_well in wells else wells[0],
                [{"label": real, "value": real} for real in reals],
                state_real if state_real in reals else reals[0],
            )

        @callback(
            Output(
                self.layout_element(WellControlView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.INCLUDE_BHP)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(
                    WellControlPressurePlotOptions.Ids.PRESSURE_PLOT_MODE
                )
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(
                    WellControlPressurePlotOptions.Ids.DISPLAY_CTRL_MODE_BAR
                )
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.SHARED_X_AXIS)
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
        ) -> Component:
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

        @callback(
            Output(
                self.settings_group(self.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.REALIZATION_BOX)
                .to_string(),
                component_property="style",
            ),
            Input(
                self.settings_group(self.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(
                    WellControlPressurePlotOptions.Ids.PRESSURE_PLOT_MODE
                )
                .to_string(),
                "value",
            ),
        )
        def _show_hide_single_real_options(pressure_plot_mode: str) -> Dict[str, str]:
            """Hides or unhides the realization dropdown according to whether mean
            or single realization is selected.
            """
            if PressurePlotMode(pressure_plot_mode) == PressurePlotMode.MEAN:
                return {"display": "none"}
            return {"display": "block"}
