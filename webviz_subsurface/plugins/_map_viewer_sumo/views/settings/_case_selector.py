from typing import List, Tuple, Dict, Optional

from dash.development.base_component import Component
from dash import Input, Output, State, callback, no_update
import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ..._layout_elements import ElementIds

from ..._mock_sumo import get_case_names, get_iteration_names


class CaseSelector(SettingsGroupABC):
    def __init__(self, field_name: str) -> None:
        super().__init__("Case selector")
        self.cases = get_case_names(field_name)

    def layout(self) -> List[Component]:

        return [
            wcc.SelectWithLabel(
                label="Case",
                id=self.register_component_unique_id(ElementIds.CASE_SELECTOR.CASE),
                multi=False,
                options=[{"label": case, "value": case} for case in self.cases],
                value=[self.cases[0]],
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
                self.component_unique_id(ElementIds.CASE_SELECTOR.ITER).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(ElementIds.CASE_SELECTOR.ITER).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.CASE_SELECTOR.CASE).to_string(),
                "value",
            ),
        )
        def _update_iteration(case: str) -> Tuple[List[Dict], str]:
            if case is None:
                return [{}], None
            iterations = get_iteration_names(case[0])
            if not iterations:
                return [{}], None
            return [
                {"label": iteration, "value": iteration} for iteration in iterations
            ], [iterations[0]]

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
