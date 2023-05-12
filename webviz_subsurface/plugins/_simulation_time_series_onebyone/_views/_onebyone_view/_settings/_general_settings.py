import datetime
from typing import List

import webviz_core_components as wcc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import LabelOptions, ScaleType
from ...._utils import date_to_str


class GeneralSettings(SettingsGroupABC):
    class Ids(StrEnum):
        OPTIONS = "options"
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
        options_id = self.register_component_unique_id(self.Ids.OPTIONS)
        return [
            wcc.Dropdown(
                label="Scale:",
                id={"id": options_id, "selector": "Scale"},
                options=[
                    {"label": "Relative value (%)", "value": ScaleType.PERCENTAGE},
                    {"label": "Relative value", "value": ScaleType.ABSOLUTE},
                    {"label": "True value", "value": ScaleType.TRUE_VALUE},
                ],
                value=ScaleType.PERCENTAGE,
                clearable=False,
            ),
            html.Div(
                style={"margin-top": "10px", "margin-bottom": "10px"},
                children=[
                    wcc.Checklist(
                        id={"id": options_id, "selector": selector},
                        options=[{"label": label, "value": "selected"}],
                        value=["selected"] if selected else [],
                    )
                    for label, selector, selected in [
                        ("Color by sensitivity", "color_by_sens", True),
                        ("Show realization points", "real_scatter", False),
                        ("Show reference on tornado", "torn_ref", True),
                        (
                            "Remove sensitivities with no impact",
                            "Remove no impact",
                            True,
                        ),
                    ]
                ],
            ),
            wcc.RadioItems(
                label="Label options:",
                id={"id": options_id, "selector": "labeloptions"},
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
                id={"id": options_id, "selector": "Reference"},
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
