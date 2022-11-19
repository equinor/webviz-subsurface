from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class FilterOption(StrEnum):
    REMOVE_SENS_WITH_NO_IMPACT = "remove-sens-with-no-impact"


class Scale(StrEnum):
    REL_VALUE_PERC = "Relative value (%)"
    REL_VALUE = "Relative value"
    TRUE_VALUE = "True value"


class ViewSettings(SettingsGroupABC):
    class IDs(StrEnum):
        REFERENCE = "reference"
        SCALE = "scale"
        SENSITIVITIES = "sensitivities"
        FILTER_OPTIONS = "plot-options"

    def __init__(
        self,
        realizations: pd.DataFrame,
        reference: str = "rms_seed",
        allow_click: bool = False,
    ) -> None:
        super().__init__("View Settings")

        self.sensnames = list(realizations["SENSNAME"].unique())

        self.initial_reference = (
            reference if reference in self.sensnames else self.sensnames[0]
        )

        self.allow_click = allow_click

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.REFERENCE),
                label="Reference",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.initial_reference,
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.SCALE),
                label="Scale",
                options=[{"label": r, "value": r} for r in Scale],
                value=Scale.REL_VALUE_PERC,
                multi=False,
                clearable=False,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(ViewSettings.IDs.SENSITIVITIES),
                label="Select sensitivities",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.sensnames,
                multi=True,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(ViewSettings.IDs.FILTER_OPTIONS),
                label="Filter options",
                options=[
                    {
                        "label": "Remove sensitivities with no impact",
                        "value": FilterOption.REMOVE_SENS_WITH_NO_IMPACT,
                    }
                ],
                value=[],
                labelStyle={"display": "block"},
            ),
        ]
