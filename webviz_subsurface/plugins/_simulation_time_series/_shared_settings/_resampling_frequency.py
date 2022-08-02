import datetime
from typing import Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers import Frequency

from .._plugin_ids import PluginIds
from ..types import ProviderSet
from ..utils import datetime_utils


class ResamplingFrequencySettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        RESAMPLING_FREQUENCY = "resampling-frequency"
        RELATIVE_DATE = "relative-date"

    def __init__(
        self,
        disable_resampling_dropdown: bool,
        selected_resampling_frequency: Frequency,
        ensembles_dates: List[datetime.datetime],
        input_provider_set: ProviderSet,
    ) -> None:
        super().__init__("Resampling frequency")
        self.disable_resampling_dropdown = disable_resampling_dropdown
        self.selected_resampling_frequency = selected_resampling_frequency
        self.ensembles_dates = ensembles_dates
        self.input_provider_set = input_provider_set

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(self.Ids.RESAMPLING_FREQUENCY),
                clearable=False,
                disabled=self.disable_resampling_dropdown,
                options=[
                    {
                        "label": frequency.value,
                        "value": frequency.value,
                    }
                    for frequency in Frequency
                ],
                value=self.selected_resampling_frequency,
                style={
                    "margin-bottom": "10px",
                },
            ),
            wcc.Label(
                "Data relative to date:",
                style={
                    "font-style": "italic",
                },
            ),
            wcc.Dropdown(
                clearable=True,
                disabled=self.disable_resampling_dropdown,
                id=self.register_component_unique_id(self.Ids.RELATIVE_DATE),
                options=[
                    {
                        "label": datetime_utils.to_str(_date),
                        "value": datetime_utils.to_str(_date),
                    }
                    for _date in sorted(self.ensembles_dates)
                ],
            ),
            wcc.Label(
                "NB: Disabled for presampled data",
                style={"font-style": "italic"}
                if self.disable_resampling_dropdown
                else {"display": "none"},
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            [
                Output(
                    self.component_unique_id(self.Ids.RELATIVE_DATE).to_string(),
                    "options",
                ),
                Output(
                    self.component_unique_id(self.Ids.RELATIVE_DATE).to_string(),
                    "value",
                ),
            ],
            [
                Input(
                    self.component_unique_id(self.Ids.RESAMPLING_FREQUENCY).to_string(),
                    "value",
                ),
            ],
            [
                State(
                    self.component_unique_id(self.Ids.RELATIVE_DATE).to_string(),
                    "options",
                ),
                State(
                    self.component_unique_id(self.Ids.RELATIVE_DATE).to_string(),
                    "value",
                ),
            ],
        )
        def _update_relative_date_dropdown(
            resampling_frequency_value: str,
            current_relative_date_options: List[dict],
            current_relative_date_value: Optional[str],
        ) -> Tuple[List[Dict[str, str]], Optional[str]]:
            """This callback updates dropdown based on selected resampling frequency selection

            If dates are not existing for a provider, the data accessor must handle invalid
            relative date selection!
            """
            resampling_frequency = Frequency.from_string_value(
                resampling_frequency_value
            )
            dates_union = self.input_provider_set.all_dates(resampling_frequency)

            # Create dropdown options:
            new_relative_date_options: List[Dict[str, str]] = [
                {
                    "label": datetime_utils.to_str(_date),
                    "value": datetime_utils.to_str(_date),
                }
                for _date in dates_union
            ]

            # Create valid dropdown value:
            new_relative_date_value = next(
                (
                    elm["value"]
                    for elm in new_relative_date_options
                    if elm["value"] == current_relative_date_value
                ),
                None,
            )

            # Prevent updates if unchanged
            if new_relative_date_options == current_relative_date_options:
                new_relative_date_options = dash.no_update
            if new_relative_date_value == current_relative_date_value:
                new_relative_date_value = dash.no_update

            return new_relative_date_options, new_relative_date_value

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.RELATIVE_DATE_DROPDOWN),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.RELATIVE_DATE).to_string(), "value"
            ),
        )
        def _update_store_relative_date(selected_data: str) -> str:
            return selected_data

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.RESAMPLING_FREQUENCY_DROPDOWN
                ),
                "data",
            ),
            Input(
                self.component_unique_id(self.Ids.RESAMPLING_FREQUENCY).to_string(),
                "value",
            ),
        )
        def _update_store_frequency_date(selected_data: str) -> str:
            return selected_data
