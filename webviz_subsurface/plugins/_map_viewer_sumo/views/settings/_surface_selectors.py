from typing import List, Tuple, Dict, Optional
from enum import Enum
from dataclasses import dataclass

from dash.development.base_component import Component
from dash import Input, Output, State, callback, no_update
import webviz_core_components as wcc
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ..._layout_elements import ElementIds
from ..._mock_sumo import (
    get_surface_attribute_names,
    get_surface_names,
    get_surface_dates,
    get_realizations,
)


@dataclass(frozen=True)
class SurfaceAddress:
    field: str
    case_name: str
    iteration_name: str
    realizations: List[int]
    aggregation: str
    surface_attribute: str
    surface_name: str
    surface_date: str


class AGGREGATIONS(str, Enum):
    SINGLE_REAL = "Single realization"
    MEAN = "Mean"
    STDDEV = "Standard deviation"
    MIN = "Min"
    MAX = "Max"
    P10 = "P10"
    P90 = "P90"


class SurfaceSelector(SettingsGroupABC):
    def __init__(self, field_name: str) -> None:
        super().__init__("Surface selectors")
        self.field_name = field_name

    def layout(self) -> List[Component]:

        return [
            wcc.SelectWithLabel(
                label="Surface attribute",
                id=self.register_component_unique_id(
                    ElementIds.SURFACE_SELECTOR.ATTRIBUTE
                ),
                multi=False,
            ),
            wcc.SelectWithLabel(
                label="Surface name",
                id=self.register_component_unique_id(ElementIds.SURFACE_SELECTOR.NAME),
                multi=False,
            ),
            wcc.SelectWithLabel(
                label="Surface date",
                id=self.register_component_unique_id(ElementIds.SURFACE_SELECTOR.DATE),
                multi=False,
            ),
            wcc.Dropdown(
                label="Aggregation",
                id=self.register_component_unique_id(
                    ElementIds.SURFACE_SELECTOR.AGGREGATION
                ),
                options=[{"label": agg, "value": agg} for agg in AGGREGATIONS],
                value=AGGREGATIONS.SINGLE_REAL,
                clearable=False,
            ),
            wcc.SelectWithLabel(
                label="Realization",
                id=self.register_component_unique_id(
                    ElementIds.SURFACE_SELECTOR.REALIZATION
                ),
                multi=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.REALIZATION
                ).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.REALIZATION
                ).to_string(),
                "value",
            ),
            Output(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.REALIZATION
                ).to_string(),
                "multi",
            ),
            Input(
                self.get_store_unique_id(ElementIds.STORES.CASE_ITER_STORE),
                "data",
            ),
            Input(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.AGGREGATION
                ).to_string(),
                "value",
            ),
        )
        def _update_realization(
            case_iter: Dict, aggregation: str
        ) -> Tuple[List[Dict], int]:
            if not case_iter:
                return no_update
            agg = AGGREGATIONS(aggregation)
            case = case_iter["case"][0]
            iteration = case_iter["iteration"][0]
            realizations = get_realizations(
                field_name=self.field_name, case_name=case, iteration_name=iteration
            )
            if agg == AGGREGATIONS.SINGLE_REAL:
                selected_reals = [realizations[0]]
                multi = False
            else:
                selected_reals = realizations
                multi = True

            return (
                [{"label": attr, "value": attr} for attr in realizations],
                selected_reals,
                multi,
            )

        @callback(
            Output(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.ATTRIBUTE
                ).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.ATTRIBUTE
                ).to_string(),
                "value",
            ),
            Input(
                self.get_store_unique_id(ElementIds.STORES.CASE_ITER_STORE),
                "data",
            ),
        )
        def _update_surface_attribute(case_iter: Dict) -> Tuple[List[Dict], str]:
            if not case_iter:
                return no_update
            case = case_iter["case"][0]
            iteration = case_iter["iteration"][0]
            attributes = get_surface_attribute_names(
                field_name=self.field_name, case_name=case, iteration_name=iteration
            )
            return [{"label": attr, "value": attr} for attr in attributes], [
                attributes[0]
            ]

        @callback(
            Output(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.NAME).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.NAME).to_string(),
                "value",
            ),
            Output(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.DATE).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.DATE).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.ATTRIBUTE
                ).to_string(),
                "value",
            ),
            State(
                self.get_store_unique_id(ElementIds.STORES.CASE_ITER_STORE),
                "data",
            ),
        )
        def _update_surface_names_and_dates(
            attribute_name: str, case_iter: Dict
        ) -> Tuple[List[Dict], str, List[Dict], str]:
            case = case_iter["case"][0]
            iteration = case_iter["iteration"][0]
            if not case_iter or not attribute_name:
                return no_update, no_update, no_update, no_update
            attribute_name = attribute_name[0]
            surface_names = get_surface_names(
                field_name=self.field_name,
                case_name=case,
                iteration_name=iteration,
                attribute_name=attribute_name,
            )
            surface_dates = get_surface_dates(
                field_name=self.field_name,
                case_name=case,
                iteration_name=iteration,
                attribute_name=attribute_name,
            )
            return (
                [{"label": name, "value": name} for name in surface_names],
                [surface_names][0],
                [{"label": date, "value": date} for date in surface_dates],
                [surface_dates][0],
            )

        def _update_surface_attribute(case_iter: Dict) -> Tuple[List[Dict], str]:
            if not case_iter:
                return no_update
            case = case_iter["case"][0]
            iteration = case_iter["iteration"][0]
            attributes = get_surface_attribute_names(
                field_name=self.field_name, case_name=case, iteration_name=iteration
            )
            return [{"label": attr, "value": attr} for attr in attributes], [
                attributes[0]
            ]

        @callback(
            Output(
                self.get_store_unique_id(ElementIds.STORES.SURFACE_ADDRESS_STORE),
                "data",
            ),
            Input(
                self.get_store_unique_id(ElementIds.STORES.CASE_ITER_STORE),
                "data",
            ),
            Input(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.ATTRIBUTE
                ).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.NAME).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(ElementIds.SURFACE_SELECTOR.DATE).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.REALIZATION
                ).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    ElementIds.SURFACE_SELECTOR.AGGREGATION
                ).to_string(),
                "value",
            ),
        )
        def _update_surface_names_and_dates(
            case_iter: Dict,
            surface_attribute: str,
            surface_name: str,
            surface_date: str,
            realizations: List[int],
            aggregation: str,
        ) -> Dict:
            if any(
                el is None
                for el in [
                    case_iter,
                    surface_attribute,
                    surface_name,
                    surface_date,
                    realizations,
                    aggregation,
                ]
            ):
                return {}

            case = case_iter["case"][0]
            iteration = case_iter["iteration"][0]

            address = SurfaceAddress(
                field=self.field_name,
                case_name=case,
                iteration_name=iteration,
                realizations=realizations,
                aggregation=aggregation,
                surface_attribute=surface_attribute,
                surface_name=surface_name,
                surface_date=surface_date,
            )
            print(address)
            return address
