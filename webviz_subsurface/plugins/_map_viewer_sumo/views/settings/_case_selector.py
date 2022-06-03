from typing import List, Tuple, Dict, Optional

from dash.development.base_component import Component
from dash import Input, Output, State, callback, no_update
import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ..._layout_elements import ElementIds

# from ..._mock_sumo import get_case_names, get_iteration_names

from webviz_subsurface._providers.ensemble_surface_provider import (
    EnsembleProviderDealer,
)


class CaseSelector(SettingsGroupABC):
    def __init__(
        self, provider_dealer: EnsembleProviderDealer, field_name: str
    ) -> None:
        super().__init__("Case selector")
        self._field_name = field_name
        self._provider_dealer = provider_dealer

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Field",
                id=self.register_component_unique_id(ElementIds.CASE_SELECTOR.FIELD),
                multi=False,
                options=[{"label": self._field_name, "value": self._field_name}],
                value=[self._field_name],
            ),
            wcc.SelectWithLabel(
                label="Case",
                id=self.register_component_unique_id(ElementIds.CASE_SELECTOR.CASE),
                multi=False,
            ),
            wcc.SelectWithLabel(
                label="Iteration",
                id=self.register_component_unique_id(ElementIds.CASE_SELECTOR.ITER),
                multi=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(ElementIds.CASE_SELECTOR.CASE).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(ElementIds.CASE_SELECTOR.CASE).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.FIELD).to_string(),
                "value",
            ),
        )
        def _update_case(field_names: list) -> Tuple[List[Dict], str]:
            print(f"_update_case() {type(field_names)=}  {field_names=}")

            if field_names is None:
                return [{}], None

            case_names = self._provider_dealer.case_names(field_name=field_names[0])
            print(f"{case_names=}")

            if not case_names:
                return [{}], None

            return [
                {"label": case_name, "value": case_name} for case_name in case_names
            ], [case_names[-1]]

        @callback(
            Output(
                self.component_unique_id(ElementIds.CASE_SELECTOR.ITER).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(ElementIds.CASE_SELECTOR.ITER).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.FIELD).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.CASE).to_string(),
                "value",
            ),
        )
        def _update_iteration(
            field_names: list, case_names: list
        ) -> Tuple[List[Dict], str]:
            print(f"_update_iteration() {type(field_names)=}  {field_names=}")
            print(f"_update_iteration() {type(case_names)=}  {case_names=}")

            if field_names is None or case_names is None:
                return [{}], None

            iteration_ids = self._provider_dealer.iteration_ids(
                field_name=field_names[0], case_name=case_names[0]
            )
            print(f"_update_iteration() {iteration_ids=}")

            if not iteration_ids:
                return [{}], None

            return [
                {"label": iter_id, "value": iter_id} for iter_id in iteration_ids
            ], [iteration_ids[0]]

        @callback(
            Output(
                self.get_store_unique_id(ElementIds.STORES.CASE_ITER_STORE),
                "data",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.CASE).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.ITER).to_string(),
                "value",
            ),
        )
        def _update_case_iter_store(case: str, iteration: str) -> Dict:
            if not case or not iteration:
                return {}
            return {"case": case, "iteration": iteration}
