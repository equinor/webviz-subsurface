import datetime
from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .._utils import datetime_utils


class ResamplingFrequencySettings(SettingsGroupABC):
    class Ids(StrEnum):
        RESAMPLING_FREQUENCY_DROPDOWN = "resampling-frequency-dropdown"
        RELATIVE_DATE_DROPDOWN = "relative-date-dropdown"

    def __init__(
        self,
        disable_resampling_dropdown: bool,
        selected_resampling_frequency: Frequency,
        ensembles_dates: List[datetime.datetime],
        input_provider_set: EnsembleSummaryProviderSet,
    ) -> None:
        super().__init__("Resampling frequency")
        self._disable_resampling_dropdown = disable_resampling_dropdown
        self._selected_resampling_frequency = selected_resampling_frequency
        self._ensembles_dates = ensembles_dates
        self._input_provider_set = input_provider_set

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(
                    ResamplingFrequencySettings.Ids.RESAMPLING_FREQUENCY_DROPDOWN
                ),
                clearable=False,
                disabled=self._disable_resampling_dropdown,
                options=[
                    {
                        "label": frequency.value,
                        "value": frequency.value,
                    }
                    for frequency in Frequency
                ],
                value=self._selected_resampling_frequency,
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
                disabled=self._disable_resampling_dropdown,
                id=self.register_component_unique_id(
                    ResamplingFrequencySettings.Ids.RELATIVE_DATE_DROPDOWN
                ),
                options=[
                    {
                        "label": datetime_utils.to_str(_date),
                        "value": datetime_utils.to_str(_date),
                    }
                    for _date in sorted(self._ensembles_dates)
                ],
            ),
            wcc.Label(
                "NB: Disabled for pre-sampled data",
                style={"font-style": "italic"}
                if self._disable_resampling_dropdown
                else {"display": "none"},
            ),
        ]
