from typing import Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .._types import DeltaEnsemble
from .._utils.delta_ensemble_utils import create_delta_ensemble_names


def _create_delta_ensemble_table_column_data(
    column_name: str, ensemble_names: List[str]
) -> List[Dict[str, str]]:
    return [{column_name: elm} for elm in ensemble_names]


class EnsemblesSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLES_DROPDOWN = "ensembles-dropdown"
        DELTA_ENSEMBLE = "delta-ensemble"
        DELTA_ENSEMBLE_A_DROPDOWN = "delta-ensemble-a-dropdown"
        DELTA_ENSEMBLE_B_DROPDOWN = "delta-ensemble-b-dropdown"
        DELTA_ENSEMBLE_CREATE_BUTTON = "delta-ensemble-create-button"
        CREATED_DELTA_ENSEMBLES_STORE = "created-delta-ensembles-store"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "create-delta-ensemble-names-table"
        CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
            "create-delta-ensemble-names-table-column"
        )

    def __init__(
        self, ensembles_names: List[str], input_provider_set: EnsembleSummaryProviderSet
    ) -> None:
        super().__init__("Ensembles")
        self._ensembles = ensembles_names
        self._input_provider_set = input_provider_set

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Selected ensembles",
                id=self.register_component_unique_id(
                    EnsemblesSettings.Ids.ENSEMBLES_DROPDOWN
                ),
                clearable=False,
                multi=True,
                options=[
                    {"label": ensemble, "value": ensemble}
                    for ensemble in self._ensembles
                ],
                value=None if len(self._ensembles) <= 0 else [self._ensembles[0]],
            ),
            wcc.Selectors(
                label="Delta Ensembles",
                id=self.register_component_unique_id(
                    EnsemblesSettings.Ids.DELTA_ENSEMBLE
                ),
                children=self._delta_ensemble_creator_layout(),
            ),
        ]

    def _delta_ensemble_creator_layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.Dropdown(
                    label="Ensemble A",
                    id=self.register_component_unique_id(
                        EnsemblesSettings.Ids.DELTA_ENSEMBLE_A_DROPDOWN
                    ),
                    clearable=False,
                    options=[{"label": i, "value": i} for i in self._ensembles],
                    value=self._ensembles[0],
                    style={"min-width": "60px"},
                ),
                wcc.Dropdown(
                    label="Ensemble B",
                    id=self.register_component_unique_id(
                        EnsemblesSettings.Ids.DELTA_ENSEMBLE_B_DROPDOWN
                    ),
                    clearable=False,
                    options=[{"label": i, "value": i} for i in self._ensembles],
                    value=self._ensembles[-1],
                    style={"min-width": "60px"},
                ),
                html.Button(
                    "Create",
                    id=self.register_component_unique_id(
                        EnsemblesSettings.Ids.DELTA_ENSEMBLE_CREATE_BUTTON
                    ),
                    n_clicks=0,
                    style={
                        "margin-top": "5px",
                        "margin-bottom": "5px",
                        "min-width": "20px",
                    },
                ),
                self._delta_ensemble_table_layout(),
                dcc.Store(
                    id=self.register_component_unique_id(
                        EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLES_STORE
                    ),
                    data=[],
                ),  # TODO: Add predefined deltas?
            ]
        )

    def _delta_ensemble_table_layout(self) -> dash_table.DataTable:
        return dash_table.DataTable(
            id=self.register_component_unique_id(
                EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE
            ),
            columns=(
                [
                    {
                        "id": self.register_component_unique_id(
                            EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
                        ),
                        "name": "Created Delta (A-B)",
                    }
                ]
            ),
            data=[],
            fixed_rows={"headers": True},
            style_as_list_view=True,
            style_cell={"textAlign": "left"},
            style_header={"fontWeight": "bold"},
            style_table={
                "maxHeight": "150px",
                "overflowY": "auto",
            },
            editable=False,
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLES_STORE
                ).to_string(),
                "data",
            ),
            Output(
                self.component_unique_id(
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE
                ).to_string(),
                "data",
            ),
            Output(
                self.component_unique_id(
                    EnsemblesSettings.Ids.ENSEMBLES_DROPDOWN
                ).to_string(),
                "options",
            ),
            Input(
                self.component_unique_id(
                    EnsemblesSettings.Ids.DELTA_ENSEMBLE_CREATE_BUTTON
                ).to_string(),
                "n_clicks",
            ),
            State(
                self.component_unique_id(
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLES_STORE
                ).to_string(),
                "data",
            ),
            State(
                self.component_unique_id(
                    EnsemblesSettings.Ids.DELTA_ENSEMBLE_A_DROPDOWN
                ).to_string(),
                "value",
            ),
            State(
                self.component_unique_id(
                    EnsemblesSettings.Ids.DELTA_ENSEMBLE_B_DROPDOWN
                ).to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_created_delta_ensembles_names(
            n_clicks: int,
            existing_delta_ensembles: List[DeltaEnsemble],
            ensemble_a: str,
            ensemble_b: str,
        ) -> Tuple[List[DeltaEnsemble], List[Dict[str, str]], List[Dict[str, str]]]:
            if n_clicks is None or n_clicks <= 0:
                raise PreventUpdate

            delta_ensemble = DeltaEnsemble(ensemble_a=ensemble_a, ensemble_b=ensemble_b)
            if delta_ensemble in existing_delta_ensembles:
                raise PreventUpdate

            new_delta_ensembles = existing_delta_ensembles
            new_delta_ensembles.append(delta_ensemble)

            # Create delta ensemble names
            new_delta_ensemble_names = create_delta_ensemble_names(new_delta_ensembles)

            table_data = _create_delta_ensemble_table_column_data(
                self.component_unique_id(
                    EnsemblesSettings.Ids.CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN
                ).to_string(),
                new_delta_ensemble_names,
            )

            ensemble_options = [
                {"label": ensemble, "value": ensemble}
                for ensemble in self._input_provider_set.provider_names()
            ]
            for elm in new_delta_ensemble_names:
                ensemble_options.append({"label": elm, "value": elm})

            return (new_delta_ensembles, table_data, ensemble_options)
