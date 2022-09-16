from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import Input, Output, State, callback, html
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from ..._utils import WellCompletionDataModel
from ._view_element import WellCompletionViewElement


class DataMode(StrEnum):
    AGGREGATED = "aggregated"
    SINGLE_REAL = "single-real"


class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        DATA_MODE = "mode"
        REALIZATION = "realization"
        REAL_BLOCK = "real-block"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Settings")
        self._ensembles = ensembles

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.Ids.ENSEMBLE),
                label="Ensemble",
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                clearable=False,
                value=self._ensembles[0],
                persistence=True,
                persistence_type="session",
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(ViewSettings.Ids.DATA_MODE),
                label="Aggregated or single realization",
                options=[
                    {
                        "label": "Aggregated",
                        "value": DataMode.AGGREGATED,
                    },
                    {
                        "label": "Single realization",
                        "value": DataMode.SINGLE_REAL,
                    },
                ],
                value=DataMode.AGGREGATED,
            ),
            html.Div(
                id=self.register_component_unique_id(ViewSettings.Ids.REAL_BLOCK),
                children=wcc.Dropdown(
                    id=self.register_component_unique_id(ViewSettings.Ids.REALIZATION),
                    label="Realization",
                    options=[],
                    multi=False,
                ),
            ),
        ]


class WellCompletionView(ViewABC):
    class Ids(StrEnum):
        VIEW_ELEMENT = "view-element"
        SETTINGS = "settings"

    def __init__(self, data_models: Dict[str, WellCompletionDataModel]) -> None:
        super().__init__("Well Completion")

        self._data_models = data_models

        self.add_settings_group(
            ViewSettings(list(self._data_models.keys())),
            WellCompletionView.Ids.SETTINGS,
        )

        column = self.add_column()
        column.add_view_element(
            WellCompletionViewElement(), WellCompletionView.Ids.VIEW_ELEMENT
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(WellCompletionView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellCompletionViewElement.Ids.COMPONENT)
                .to_string(),
                "children",
            ),
            Output(
                self.view_element(WellCompletionView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellCompletionViewElement.Ids.COMPONENT)
                .to_string(),
                "style",
            ),
            Input(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.DATA_MODE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _render_well_completions(
            ensemble_name: str, data_mode: DataMode, real: int
        ) -> Tuple:

            data = self._data_models[ensemble_name].create_ensemble_dataset(
                realization=real if data_mode == DataMode.SINGLE_REAL else None
            )
            no_leaves = _count_leaves(data["stratigraphy"])
            return (
                wsc.WellCompletions(id="well-completion-component", data=data),
                {
                    "height": no_leaves * 50 + 180,
                    "min-height": 500,
                    "width": "98%",
                },
            )

        @callback(
            Output(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.REALIZATION)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
        )
        def _update_realization_dropdown(
            ensemble: str, state_real: int
        ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
            """Updates the ealization dropdown with ensemble values"""
            reals = self._data_models[ensemble].realizations
            return (
                [{"label": real, "value": real} for real in reals],
                state_real if state_real in reals else reals[0],
            )

        @callback(
            Output(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.REAL_BLOCK)
                .to_string(),
                component_property="style",
            ),
            Input(
                self.settings_group(WellCompletionView.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.DATA_MODE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _show_hide_single_real_options(data_mode: DataMode) -> Dict[str, str]:
            """Hides or unhides the realization dropdown according to whether mean
            or single realization is selected.
            """
            if data_mode == DataMode.AGGREGATED:
                return {"display": "none"}
            return {"display": "block"}


def _count_leaves(stratigraphy: List[Dict[str, Any]]) -> int:
    """Counts the number of leaves in the stratigraphy tree"""
    return sum(
        _count_leaves(zonedict["subzones"]) if "subzones" in zonedict else 1
        for zonedict in stratigraphy
    )
