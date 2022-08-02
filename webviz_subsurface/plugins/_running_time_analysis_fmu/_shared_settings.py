from typing import List, Tuple, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class RunningTimeAnalysisFmuSettings(SettingsGroupABC):

    # pylint: disable=too-few-public-methods
    class Ids:
        MODE = "mode-1"
        ENSEMBLE = "ensemble"
        COLORING = "coloring"
        COLOR_LABEL = "color-label"
        FILTERING = "filtering"
        FILTER_SHORT = "filter-short"
        REMOVE_CONSTANT = "remove-constant"
        FILTER_PARAMS = "filter-params"

    COLOR_MATRIX_BY_LABELS = [
        "Same job in ensemble",
        "Slowest job in realization",
        "Slowest job in ensemble",
    ]
    COLOR_PARCOORD_BY_LABELS = [
        "Successful/failed realization",
        "Running time of realization",
    ]

    def __init__(
        self,
        real_status_df: pd.DataFrame,
        ensembles: list,
        visual_parameters: list,
        plugin_paratamters: List[str],
        filter_shorter: Union[int, float] = 10,
    ) -> None:
        super().__init__("Data filter")
        self.real_status_df = real_status_df
        self.ensembles = ensembles
        self.filter_shorter = filter_shorter
        self.parameters = plugin_paratamters
        self.visual_parameters = visual_parameters

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                label="Mode",
                id=self.register_component_unique_id(self.Ids.MODE),
                options=[
                    {
                        "label": "Running time matrix",
                        "value": "running_time_matrix",
                    },
                    {
                        "label": "Parameter parallel coordinates",
                        "value": "parallel_coordinates",
                    },
                ],
                value="running_time_matrix",
            ),
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                value=self.ensembles[0],
                clearable=False,
            ),
            wcc.Label(
                id=self.register_component_unique_id(self.Ids.COLOR_LABEL),
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(self.Ids.COLORING),
                options=[
                    {"label": rel, "value": rel} for rel in self.COLOR_MATRIX_BY_LABELS
                ],
                value=self.COLOR_MATRIX_BY_LABELS[0],
                clearable=False,
            ),
            wcc.Selectors(
                label="Filtering jobs",
                id=self.register_component_unique_id(self.Ids.FILTERING),
                children=[
                    wcc.Checklist(
                        id=self.register_component_unique_id(self.Ids.FILTER_SHORT),
                        labelStyle={"display": "block"},
                        options=[
                            {
                                "label": "Slowest in ensemble less than "
                                f"{self.filter_shorter}s",
                                "value": "filter_short",
                            },
                        ],
                        value=["filter_short"],
                    ),
                    wcc.Checklist(
                        id=self.register_component_unique_id(self.Ids.REMOVE_CONSTANT),
                        labelStyle={"display": "none"},
                        options=[
                            {
                                "label": " Remove constant ",
                                "value": "remove_constant",
                            },
                        ],
                        value=[],
                    ),
                    wcc.SelectWithLabel(
                        id=self.register_component_unique_id(self.Ids.FILTER_PARAMS),
                        style={"display": "none"},
                        options=[
                            {"label": param, "value": param}
                            for param in self.parameters
                        ],
                        multi=True,
                        value=self.visual_parameters,
                        size=min(50, len(self.visual_parameters)),
                    ),
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.FILTER_PARAMS).to_string(), "options"
            ),
            Output(
                self.component_unique_id(self.Ids.FILTER_PARAMS).to_string(), "value"
            ),
            Input(
                self.component_unique_id(self.Ids.REMOVE_CONSTANT).to_string(), "value"
            ),
            State(self.component_unique_id(self.Ids.ENSEMBLE).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.COLORING).to_string(), "value"),
        )
        def _update_filter_parameters(
            remove_constant: str, ens: str, coloring: str
        ) -> Tuple:
            if remove_constant is None:
                raise PreventUpdate

            dimentions_params = []

            if coloring == "Successful/failed realization":
                plot_df = self.real_status_df[self.real_status_df["ENSEMBLE"] == ens]
            else:
                plot_df = self.real_status_df[
                    (self.real_status_df["ENSEMBLE"] == ens)
                    & (self.real_status_df["STATUS_BOOL"] == 1)
                ]
            if remove_constant == ["remove_constant"]:
                for param in self.parameters:
                    if len(np.unique(plot_df[param].values)) > 1:
                        dimentions_params.append(param)
            else:
                dimentions_params = self.parameters

            filter_parame_options = [
                {"label": param, "value": param} for param in dimentions_params
            ]
            filter_parame_value = dimentions_params

            return (filter_parame_options, filter_parame_value)

        @callback(
            Output(
                self.component_unique_id(self.Ids.FILTER_SHORT).to_string(),
                "labelStyle",
            ),
            Output(
                self.component_unique_id(self.Ids.REMOVE_CONSTANT).to_string(),
                "labelStyle",
            ),
            Output(
                self.component_unique_id(self.Ids.FILTER_PARAMS).to_string(),
                "style",
            ),
            Output(
                self.component_unique_id(self.Ids.COLOR_LABEL).to_string(), "children"
            ),
            Output(self.component_unique_id(self.Ids.COLORING).to_string(), "options"),
            Output(self.component_unique_id(self.Ids.COLORING).to_string(), "value"),
            Input(self.component_unique_id(self.Ids.MODE).to_string(), "value"),
        )
        def _update_color(selected_mode: str) -> Tuple:
            # label = None
            # value = None

            if selected_mode == "running_time_matrix":
                label = "Color jobs relative to running time of:"
                options = [
                    {"label": rel, "value": rel} for rel in self.COLOR_MATRIX_BY_LABELS
                ]
                value = self.COLOR_MATRIX_BY_LABELS[0]

                return (
                    {"display": "block"},
                    {"display": "none"},
                    {"display": "none"},
                    label,
                    options,
                    value,
                )

            options = [
                {"label": rel, "value": rel} for rel in self.COLOR_PARCOORD_BY_LABELS
            ]
            value = self.COLOR_PARCOORD_BY_LABELS[0]

            return (
                {"display": "none"},
                {"display": "block"},
                {"display": "block"},
                "Color realizations relative to:",
                options,
                value,
            )
