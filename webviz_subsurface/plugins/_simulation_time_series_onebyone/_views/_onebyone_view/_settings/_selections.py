import datetime
from typing import List

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ......_providers import Frequency
from .._utils import date_from_str, date_to_str


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        VECTOR_SELECTOR = "vector-selector"
        SELECTED_DATE = "selected-date"
        DATE_SLIDER = "date-slider"

    def __init__(
        self, ensembles: List[str], vectors: List[str], dates: List[datetime.datetime]
    ) -> None:
        super().__init__("Selections")
        self._ensembles = ensembles
        self._vectors = vectors
        self._dates = dates

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                multi=False,
                value=self._ensembles[0],
                clearable=False,
            ),
            wsc.VectorSelector(
                label="Time Series",
                id=self.register_component_unique_id(self.Ids.VECTOR_SELECTOR),
                maxNumSelectedNodes=1,
                data=self._vectors,
                persistence=True,
                persistence_type="session",
                selectedTags=["FOPT"] if "FOPT" in self._vectors else None,
                numSecondsUntilSuggestionsAreShown=0.5,
                lineBreakAfterTag=True,
            ),
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    wcc.Label("Date:"),
                    wcc.Label(
                        date_to_str(self._dates[-1]),
                        id=self.register_component_unique_id(self.Ids.SELECTED_DATE),
                        style={"margin-left": "10px"},
                    ),
                ],
            ),
            wcc.Slider(
                id=self.register_component_unique_id(self.Ids.DATE_SLIDER),
                value=len(self._dates) - 1,
                min=0,
                max=len(self._dates) - 1,
                step=1,
                included=False,
                marks={
                    idx: {
                        "label": date_to_str(self._dates[idx]),
                        "style": {"white-space": "nowrap"},
                    }
                    for idx in [0, len(self._dates) - 1]
                },
            ),
        ]
