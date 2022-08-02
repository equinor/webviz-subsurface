from typing import List, Optional

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._utils.formatting import printable_int_list

from .._plugin_ids import PluginIds
from ..types import StatisticsFromOptions


class FilterRealizationSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        REALIZATIONS_FILTER_SPAN = "realization-filter-span"
        STATISTICS_FROM_RADIO_ITEMS = "statistics-from-radio-items"
        REALIZATIONS_FILTER_SELECTOR = "realizations-filter-selector"

    def __init__(self, realizations: List[int]) -> None:
        super().__init__("Filter Realizations")
        self.realizations = realizations

    def layout(self) -> List[Component]:
        return [
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Label(
                        "Realizations: ",
                        style={"font-weight": "bold"},
                    ),
                    html.Label(
                        id=self.register_component_unique_id(
                            self.Ids.REALIZATIONS_FILTER_SPAN
                        ),
                        style={
                            "margin-left": "10px",
                            "margin-bottom": "5px",
                        },
                        children=f"{min(self.realizations)}-{max(self.realizations)}",
                    ),
                ],
            ),
            wcc.RadioItems(
                label="Statistics calculated from:",
                id=self.register_component_unique_id(
                    self.Ids.STATISTICS_FROM_RADIO_ITEMS
                ),
                style={"margin-bottom": "10px"},
                options=[
                    {
                        "label": "All",
                        "value": StatisticsFromOptions.ALL_REALIZATIONS.value,
                    },
                    {
                        "label": "Selected",
                        "value": StatisticsFromOptions.SELECTED_REALIZATIONS.value,
                    },
                ],
                value=StatisticsFromOptions.ALL_REALIZATIONS.value,
                vertical=False,
            ),
            wcc.Select(
                id=self.register_component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ),
                options=[{"label": i, "value": i} for i in self.realizations],
                value=self.realizations,
                size=min(10, len(self.realizations)),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.REALIZATIONS_FILTER_SPAN).to_string(),
                "children",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _update_realization_range(realizations: List[int]) -> Optional[str]:
            if not realizations:
                raise PreventUpdate

            realizations_filter_text = printable_int_list(realizations)

            return realizations_filter_text

        @callback(
            Output(
                self.component_unique_id(
                    self.Ids.STATISTICS_FROM_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _update_realization_option(selected_value: List[int]) -> str:
            if len(selected_value) == len(self.realizations):
                return StatisticsFromOptions.ALL_REALIZATIONS.value
            return StatisticsFromOptions.SELECTED_REALIZATIONS.value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.REALIZATIONS_FILTER_SELECTOR),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _update_store_filter_selector_value(selected_data: List[int]) -> List[int]:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.REALIZATIONS_FILTER_SELECTOR_ID
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "id",
            ),
        )
        def _update_store_filter_selector_id(selected_data: str) -> str:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.STATISTICS_FROM_RADIO_ITEMS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    self.Ids.STATISTICS_FROM_RADIO_ITEMS
                ).to_string(),
                "value",
            ),
        )
        def _update_store_statistic_radio(selected_data: str) -> str:
            return selected_data
