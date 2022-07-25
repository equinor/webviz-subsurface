from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._business_logic import RftPlotterDataModel


class FilterLayout(SettingsGroupABC):
    class Ids:
        FILTER_ENSEMBLES = {
            "misfitplot": "ensembles-misfit",
            "crossplot": "ensembles-crossplot",
            "errorplot": "ensembles-errorplot",
        }
        FILTER_WELLS = {
            "misfitplot": "well-misfit",
            "crossplot": "well-crossplot",
            "errorplot": "well-errorplot",
        }
        FILTER_ZONES = {
            "misfitplot": "zones-misfit",
            "crossplot": "zones-crossplot",
            "errorplot": "zones-errorplot",
        }
        FILTER_DATES = {
            "misfitplot": "dates-misfit",
            "crossplot": "dates-crossplot",
            "errorplot": "dates-errorplot",
        }

    def __init__(self, datamodel: RftPlotterDataModel, tab: str) -> None:
        super().__init__("Selector")
        self.tab = tab
        self.ensembles = datamodel.ensembles
        self.well_names = datamodel.well_names
        self.zone_names = datamodel.zone_names
        self.dates = datamodel.dates

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Ensembles",
                size=min(4, len(self.ensembles)),
                id=self.register_component_unique_id(
                    self.Ids.FILTER_ENSEMBLES[self.tab]
                ),
                options=[{"label": name, "value": name} for name in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Wells",
                size=min(20, len(self.well_names)),
                id=self.register_component_unique_id(self.Ids.FILTER_WELLS[self.tab]),
                options=[{"label": name, "value": name} for name in self.well_names],
                value=self.well_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Zones",
                size=min(10, len(self.zone_names)),
                id=self.register_component_unique_id(self.Ids.FILTER_ZONES[self.tab]),
                options=[{"label": name, "value": name} for name in self.zone_names],
                value=self.zone_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Dates",
                size=min(10, len(self.dates)),
                id=self.register_component_unique_id(self.Ids.FILTER_DATES[self.tab]),
                options=[{"label": name, "value": name} for name in self.dates],
                value=self.dates,
                multi=True,
            ),
        ]
