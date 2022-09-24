from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ._utils import RftPlotterDataModel


class FilterLayout(SettingsGroupABC):
    class Ids(StrEnum):
        FILTER_ENSEMBLES = "filter-ensembles"
        FILTER_WELLS = "filter-wells"
        FILTER_ZONES = "filter-zones"
        FILTER_DATES = "filter-dates"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Filters")
        self._ensembles = datamodel.ensembles
        self._well_names = datamodel.well_names
        self._zone_names = datamodel.zone_names
        self._dates = datamodel.dates

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Ensembles",
                size=min(4, len(self._ensembles)),
                id=self.register_component_unique_id(self.Ids.FILTER_ENSEMBLES),
                options=[{"label": name, "value": name} for name in self._ensembles],
                value=self._ensembles,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Wells",
                size=min(15, len(self._well_names)),
                id=self.register_component_unique_id(self.Ids.FILTER_WELLS),
                options=[{"label": name, "value": name} for name in self._well_names],
                value=self._well_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Zones",
                size=min(10, len(self._zone_names)),
                id=self.register_component_unique_id(self.Ids.FILTER_ZONES),
                options=[{"label": name, "value": name} for name in self._zone_names],
                value=self._zone_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Dates",
                size=min(10, len(self._dates)),
                id=self.register_component_unique_id(self.Ids.FILTER_DATES),
                options=[{"label": name, "value": name} for name in self._dates],
                value=self._dates,
                multi=True,
            ),
        ]
