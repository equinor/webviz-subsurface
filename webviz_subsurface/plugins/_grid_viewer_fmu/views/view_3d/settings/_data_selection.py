from typing import Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback, no_update
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers.ensemble_grid_provider import EnsembleGridProvider
from webviz_subsurface.plugins._grid_viewer_fmu._types import PROPERTYTYPE


def list_to_options(values: List) -> List:
    return [{"value": val, "label": val} for val in values]


class DataSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ID = "data-selectors"
        REALIZATIONS = "realizations"
        STATIC_DYNAMIC = "static-dynamic"
        PROPERTIES = "properties"
        DATES = "dates"
        WELLS = "wells"

    def __init__(self, grid_provider: EnsembleGridProvider) -> None:
        super().__init__("Data Selection")
        self.grid_provider = grid_provider
        self.static_dynamic_options = []
        self.static_dynamic_value = None

        if grid_provider.static_property_names():
            self.static_dynamic_options.append(
                {"label": PROPERTYTYPE.STATIC, "value": PROPERTYTYPE.STATIC}
            )
            self.static_dynamic_value = PROPERTYTYPE.STATIC

        if grid_provider.dynamic_property_names():
            self.static_dynamic_options.append(
                {"label": PROPERTYTYPE.DYNAMIC, "value": PROPERTYTYPE.DYNAMIC}
            )
            if self.static_dynamic_value is None:
                self.static_dynamic_value = PROPERTYTYPE.DYNAMIC

    def layout(self) -> List[Component]:

        return [
            wcc.SelectWithLabel(
                label="Realizations",
                id=self.register_component_unique_id(DataSettings.Ids.REALIZATIONS),
                multi=False,
                options=list_to_options(self.grid_provider.realizations()),
                value=[self.grid_provider.realizations()[0]],
            ),
            wcc.RadioItems(
                label="Grid property",
                vertical=False,
                id=self.register_component_unique_id(DataSettings.Ids.STATIC_DYNAMIC),
                options=self.static_dynamic_options,
                value=self.static_dynamic_value,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(DataSettings.Ids.PROPERTIES),
                multi=False,
            ),
            wcc.SelectWithLabel(
                label="Timestep",
                id=self.register_component_unique_id(DataSettings.Ids.DATES),
                multi=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(DataSettings.Ids.PROPERTIES).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(DataSettings.Ids.PROPERTIES).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(DataSettings.Ids.STATIC_DYNAMIC).to_string(),
                "value",
            ),
        )
        def _populate_properties(
            static_dynamic: str,
        ) -> Tuple[List[Dict[str, str]], List[str]]:
            if PROPERTYTYPE(static_dynamic) == PROPERTYTYPE.STATIC:
                prop_names = self.grid_provider.static_property_names()

            else:
                prop_names = self.grid_provider.dynamic_property_names()

            return (
                [{"label": prop, "value": prop} for prop in prop_names],
                [prop_names[0]],
            )

        @callback(
            Output(
                self.component_unique_id(DataSettings.Ids.DATES).to_string(),
                "options",
            ),
            Output(
                self.component_unique_id(DataSettings.Ids.DATES).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(DataSettings.Ids.PROPERTIES).to_string(),
                "value",
            ),
            State(
                self.component_unique_id(DataSettings.Ids.STATIC_DYNAMIC).to_string(),
                "value",
            ),
            State(
                self.component_unique_id(DataSettings.Ids.DATES).to_string(),
                "options",
            ),
        )
        def _populate_dates(
            property_names: List[str],
            static_dynamic: str,
            current_date_options: List,
        ) -> Tuple[List[Dict[str, str]], Optional[List[str]]]:
            if PROPERTYTYPE(static_dynamic) == PROPERTYTYPE.STATIC:
                return [], None

            property_name = property_names[0]
            dates = self.grid_provider.dates_for_dynamic_property(
                property_name=property_name
            )
            dates = dates if dates else []
            current_date_options = current_date_options if current_date_options else []
            if set(dates) == {dateopt["value"] for dateopt in current_date_options}:
                return no_update, no_update
            normaldates = [datestr for datestr in dates if "_" not in datestr]
            diffdates = [datestr for datestr in dates if "_" in datestr]
            dates = normaldates + diffdates
            return (
                ([{"label": prop, "value": prop} for prop in dates]),
                [dates[0]] if dates else None,
            )
