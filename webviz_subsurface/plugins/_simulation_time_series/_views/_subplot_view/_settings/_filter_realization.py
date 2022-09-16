from typing import List, Optional

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._utils.formatting import printable_int_list

from .._types import StatisticsFromOptions


class FilterRealizationSettings(SettingsGroupABC):
    class Ids(StrEnum):
        REALIZATIONS_FILTER_SPAN = "realization-filter-span"
        STATISTICS_FROM_RADIO_ITEMS = "statistics-from-radio-items"
        REALIZATIONS_FILTER_SELECTOR = "realizations-filter-selector"

    def __init__(self, realizations: List[int]) -> None:
        super().__init__("Filter Realizations")
        self._realizations = realizations

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
                            FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SPAN
                        ),
                        style={
                            "margin-left": "10px",
                            "margin-bottom": "5px",
                        },
                        children=f"{min(self._realizations)}-{max(self._realizations)}",
                    ),
                ],
            ),
            wcc.RadioItems(
                label="Statistics calculated from:",
                id=self.register_component_unique_id(
                    FilterRealizationSettings.Ids.STATISTICS_FROM_RADIO_ITEMS
                ),
                style={"margin-bottom": "10px"},
                options=[
                    {
                        "label": "All",
                        "value": StatisticsFromOptions.ALL_REALIZATIONS,
                    },
                    {
                        "label": "Selected",
                        "value": StatisticsFromOptions.SELECTED_REALIZATIONS,
                    },
                ],
                value=StatisticsFromOptions.ALL_REALIZATIONS,
                vertical=False,
            ),
            wcc.Select(
                id=self.register_component_unique_id(
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SELECTOR
                ),
                options=[{"label": i, "value": i} for i in self._realizations],
                value=self._realizations,
                size=min(10, len(self._realizations)),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SPAN
                ).to_string(),
                "children",
            ),
            Input(
                self.component_unique_id(
                    FilterRealizationSettings.Ids.REALIZATIONS_FILTER_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_realization_range(realizations: List[int]) -> Optional[str]:
            if not realizations:
                raise PreventUpdate

            realizations_filter_text = printable_int_list(realizations)

            return realizations_filter_text
