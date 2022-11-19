from typing import List

import webviz_core_components as wcc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers import EnsembleTableProvider


class Filters(SettingsGroupABC):
    class IDs(StrEnum):
        SINGLE_FILTER = "single-filter"
        MULTI_FILTER = "multi-filter"

    def __init__(
        self,
        table_provider: EnsembleTableProvider,
        single_filters: List[str],
        multi_filters: List[str],
    ) -> None:
        super().__init__("Filters")
        self._table_provider = table_provider
        self._single_filters = single_filters
        self._multi_filters = multi_filters
        self.single_filter_id = self.register_component_unique_id(
            Filters.IDs.SINGLE_FILTER
        )
        self.multi_filter_id = self.register_component_unique_id(
            Filters.IDs.MULTI_FILTER
        )

    def layout(self) -> List[Component]:
        single_filter_elements = []

        for selector in self._single_filters:
            values = self._table_provider.get_column_data([selector])[selector].unique()

            single_filter_elements.append(
                wcc.Dropdown(
                    label=selector,
                    id={
                        "id": self.single_filter_id,
                        "name": selector,
                        "type": "single_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values[0],
                    clearable=False,
                )
            )

        multi_filter_elements = []
        for selector in self._multi_filters:
            values = self._table_provider.get_column_data([selector])[selector].unique()
            multi_filter_elements.append(
                wcc.SelectWithLabel(
                    label=selector,
                    id={
                        "id": self.multi_filter_id,
                        "name": selector,
                        "type": "multi_filter",
                    },
                    options=[{"label": val, "value": val} for val in values],
                    value=values,
                    multi=True,
                )
            )
        return [
            html.Div(
                id=self.component_unique_id(self.single_filter_id).to_string(),
                children=single_filter_elements,
            ),
            html.Div(
                id=self.component_unique_id(self.multi_filter_id).to_string(),
                children=multi_filter_elements,
            ),
        ]
