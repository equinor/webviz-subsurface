import datetime
from typing import Any, Dict, List

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import date_to_str


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        VECTOR_SELECTOR = "vector-selector"
        SELECTED_DATE = "selected-date"
        DATE_SLIDER = "date-slider"

    def __init__(
        self,
        ensembles: List[str],
        vectors: List[str],
        vector_selector_data: List[Dict[str, Any]],
        dates: List[datetime.datetime],
        initial_vector: str,
    ) -> None:
        super().__init__("Selections")
        self._ensembles = ensembles
        self._vectors = vectors
        self._vector_selector_data = vector_selector_data
        self._dates = dates
        self._initial_vector = initial_vector

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
                data=self._vector_selector_data,
                persistence=True,
                persistence_type="session",
                selectedTags=[self._initial_vector],
                numSecondsUntilSuggestionsAreShown=0.5,
                lineBreakAfterTag=True,
            ),
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    wcc.Label("Date:"),
                    wcc.Label(
                        children=date_to_str(self._dates[-1]),
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
