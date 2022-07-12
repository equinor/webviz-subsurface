from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        COUNTRY_SELECT = "country-select"
        YEAR_SLIDER = "year-slider"

    def __init__(self) -> None:
        super().__init__("Filter")

        self.countries = ['A','B','C','D','E']

        self.years = [1,2,3,4,5,6,7,8,9,10]

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.COUNTRY_SELECT),
                label="Countries",
                options=[{"label": i, "value": i} for i in self.countries],
                value=[self.countries[0]],
                multi=True,
                size=min(15, len(self.countries)),
            ),
            wcc.RangeSlider(
                id=self.register_component_unique_id(Filter.Ids.YEAR_SLIDER),
                label="Years",
                marks={y: int(y) for y in self.years[::25]},
                min=int(self.years[0]),
                max=int(self.years[-1]),
                step=1,
                value=[int(self.years[0]), int(self.years[-1])],
                tooltip=True,
                updatemode="drag",
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_COUNTRIES), "data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.COUNTRY_SELECT).to_string(),
                "value",
            ),
        )
        def _set_countries(countries: List[str]) -> List[str]:
            return countries

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_YEARS), "data"),
            Input(
                self.component_unique_id(Filter.Ids.YEAR_SLIDER).to_string(),
                "value",
            ),
        )
        def _set_years(years: List[int]) -> List[int]:
            return years