import datetime
from typing import List

import webviz_core_components as wcc
from dash import dcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import LabelOptions, ScaleType
from ...._utils import date_to_str


class GeneralSettings(SettingsGroupABC):
    class Ids(StrEnum):
        SCALE_TYPE = "scale-type"
        CHECKBOX_SETTINGS = "checkbox-settings"
        LABEL_OPTIONS = "label-options"
        REFERENCE = "reference"
        OPTIONS_STORE = "options-store"
        REAL_STORE = "real-store"
        DATE_STORE = "date-store"
        VECTOR_STORE = "vector-store"

    def __init__(
        self,
        sensitivities: List[str],
        initial_date: datetime.datetime,
        reference_sensname: str = "rms_seed",
    ) -> None:
        super().__init__("⚙️ Settings")
        self._sensitivities = sensitivities
        self._ref_sens = (
            reference_sensname
            if reference_sensname in self._sensitivities
            else self._sensitivities[0]
        )
        self._initial_date = initial_date

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Scale:",
                id=self.register_component_unique_id(self.Ids.SCALE_TYPE),
                options=[
                    {"label": "Relative value (%)", "value": ScaleType.PERCENTAGE},
                    {"label": "Relative value", "value": ScaleType.ABSOLUTE},
                    {"label": "True value", "value": ScaleType.TRUE_VALUE},
                ],
                value=ScaleType.PERCENTAGE,
                clearable=False,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(self.Ids.CHECKBOX_SETTINGS),
                style={"margin-top": "10px"},
                options=[
                    {"label": "Color by sensitivity", "value": "color-by-sens"},
                    {"label": "Show realization points", "value": "real-scatter"},
                    {"label": "Show reference on tornado", "value": "show-tornado-ref"},
                    {
                        "label": "Remove sensitivities with no impact",
                        "value": "remove-no-impact",
                    },
                ],
                value=["color-by-sens", "show-tornado-ref", "remove-no-impact"],
            ),
            wcc.RadioItems(
                label="Label options:",
                id=self.register_component_unique_id(self.Ids.LABEL_OPTIONS),
                options=[
                    {"label": "Detailed", "value": LabelOptions.DETAILED},
                    {"label": "Simple", "value": LabelOptions.SIMPLE},
                    {"label": "Hide", "value": LabelOptions.HIDE},
                ],
                vertical=False,
                value=LabelOptions.SIMPLE,
            ),
            wcc.Dropdown(
                label="Reference:",
                id=self.register_component_unique_id(self.Ids.REFERENCE),
                options=[{"label": elm, "value": elm} for elm in self._sensitivities],
                value=self._ref_sens,
                clearable=False,
            ),
            dcc.Store(self.register_component_unique_id(self.Ids.OPTIONS_STORE)),
            dcc.Store(self.register_component_unique_id(self.Ids.REAL_STORE)),
            dcc.Store(
                self.register_component_unique_id(self.Ids.DATE_STORE),
                data=date_to_str(self._initial_date),
            ),
            dcc.Store(self.register_component_unique_id(self.Ids.VECTOR_STORE)),
        ]
