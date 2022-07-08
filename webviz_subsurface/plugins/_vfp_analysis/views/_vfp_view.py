from typing import Any, Dict, List, Tuple

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._business_logic import VfpDataModel, VfpTable
from ..view_elements import VfpViewElement


class ViewSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        VFP_NUMBER = "vfp-number"

    def __init__(self, vfp_numbers: List[int]) -> None:
        super().__init__("Settings")
        self._vfp_numbers = vfp_numbers

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.Ids.VFP_NUMBER),
                label="VFP number",
                options=[{"label": vfp, "value": vfp} for vfp in self._vfp_numbers],
                clearable=False,
                value=self._vfp_numbers[0],
                persistence=True,
                persistence_type="session",
            )
        ]


class Filters(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        RATE_LABEL = "rate-label"
        PRESSURE_LABEL = "pressure-label"
        WFR_LABEL = "wfr-label"
        GFR_LABEL = "gfr-label"
        ALQ_LABEL = "alq-label"
        RATE = "RATE"
        PRESSURE = "pressure"
        WFR = "wfr"
        GFR = "gfr"
        ALQ = "alq"

    def __init__(self) -> None:
        super().__init__("Filters")

    def layout(self) -> List[Any]:
        return [
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.RATE_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.RATE),
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.PRESSURE_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.PRESSURE),
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.WFR_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.WFR),
            ),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.GFR_LABEL),
            ),
            wcc.SelectWithLabel(id=self.register_component_unique_id(Filters.Ids.GFR)),
            html.Label(
                id=self.register_component_unique_id(Filters.Ids.ALQ_LABEL),
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filters.Ids.ALQ),
            ),
        ]


class VfpView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        VIEW_ELEMENT = "view-element"
        SETTINGS = "settings"
        FILTERS = "filters"

    def __init__(self, data_model: VfpDataModel) -> None:
        super().__init__("VFP Analysis")

        self._data_model = data_model

        self.add_settings_group(
            ViewSettings(self._data_model.get_vfp_numbers()), VfpView.Ids.SETTINGS
        )
        self.add_settings_group(Filters(), VfpView.Ids.FILTERS)

        column = self.add_column()
        column.add_view_element(VfpViewElement(), VfpView.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            # Options
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.RATE)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.PRESSURE)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ)
                .to_string(),
                "options",
            ),
            # Values
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.RATE)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.PRESSURE)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ)
                .to_string(),
                "value",
            ),
            # Labels
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.RATE_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.PRESSURE_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.WFR_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.GFR_LABEL)
                .to_string(),
                "children",
            ),
            Output(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(Filters.Ids.ALQ_LABEL)
                .to_string(),
                "children",
            ),
            # Input
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ViewSettings.Ids.VFP_NUMBER)
                .to_string(),
                "value",
            ),
        )
        def _update_filters(
            vfp_number: int,
        ) -> Tuple[
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[Dict[str, float]],
            List[float],
            List[float],
            List[float],
            List[float],
            List[float],
            str,
            str,
            str,
            str,
            str,
        ]:

            vfp_table: VfpTable = self._data_model.get_vfp_table(vfp_number)
            param_data = vfp_table.get_parameter_data()

            rate_values = param_data["RATE"]["values"]
            pressure_values = param_data["PRESSURE"]["values"]
            wfr_values = param_data["WFR"]["values"]
            gfr_values = param_data["GFR"]["values"]
            alq_values = param_data["ALQ"]["values"]

            return (
                [{"label": value, "value": value} for value in rate_values],
                [{"label": value, "value": value} for value in pressure_values],
                [{"label": value, "value": value} for value in wfr_values],
                [{"label": value, "value": value} for value in gfr_values],
                [{"label": value, "value": value} for value in alq_values],
                rate_values,
                pressure_values,
                wfr_values,
                gfr_values,
                alq_values,
                param_data["RATE"]["type"].name,
                param_data["PRESSURE"]["type"].name,
                param_data["WFR"]["type"].name,
                param_data["GFR"]["type"].name,
                param_data["ALQ"]["type"].name,
            )
