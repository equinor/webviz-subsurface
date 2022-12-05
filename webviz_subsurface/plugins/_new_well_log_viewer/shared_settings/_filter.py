from typing import List

from dash import callback, Input, Output
from dash.development.base_component import Component

from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
from webviz_core_components import SelectWithLabel

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods

        WELL_SELECT = "well-select"
        LOG_SELECT = "log-select"

    def __init__(self):
        super().__init__("Filter")

        # self.countries = population_df["Country Name"].drop_duplicates().to_list()
        self.wells = ["well1", "well2", "well3"]
        self.logs = ["All logs"]

    def layout(self) -> List[Component]:
        return [
            SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.WELL_SELECT),
                label="Well",
                options=[{"label": i, "value": i} for i in self.wells],
                value=[self.wells[0]],
                multi=False,
                size=min(15, len(self.wells)),
            ),
            SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.LOG_SELECT),
                label="Log template",
                options=[{"label": i, "value": i} for i in self.logs],
                value=[self.logs[0]],
                multi=False,
                size=min(15, len(self.logs)),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.WELL), "data"),
            Input(
                self.component_unique_id(Filter.Ids.WELL_SELECT).to_string(), "value"
            ),
        )
        def _set_well(well: str) -> str:
            return well

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.LOG_TEMPLATE), "data"),
            Input(self.component_unique_id(Filter.Ids.LOG_SELECT).to_string(), "value"),
        )
        def _set_log(log: str) -> str:
            return log
