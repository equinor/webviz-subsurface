from typing import List

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import datetime_utils
from ....models import ParametersModel, SimulationTimeSeriesModel


class ParamRespSelections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        SUMVEC = "sumvec"
        DATE_SELECTED_TEXT = "date-selected-text"
        DATE_SELECTED = "date-selected"
        DATE_SLIDER = "date-slider"
        PARAMETERS = "parameters"

    def __init__(
        self, parametermodel: ParametersModel, vectormodel: SimulationTimeSeriesModel
    ) -> None:
        super().__init__("Selections")
        self._parametermodel = parametermodel
        self._vectormodel = vectormodel

    def layout(self) -> List[Component]:
        dates = self._vectormodel.dates
        ensembles = self._parametermodel.mc_ensembles
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                multi=False,
                value=ensembles[0],
                clearable=False,
            ),
            wsc.VectorSelector(
                label="Time Series",
                id=self.register_component_unique_id(self.Ids.SUMVEC),
                maxNumSelectedNodes=1,
                data=self._vectormodel.vector_selector_data,
                persistence=True,
                persistence_type="session",
                selectedTags=["FOPT"]
                if "FOPT" in self._vectormodel.vectors
                else self._vectormodel.vectors[:1],
                numSecondsUntilSuggestionsAreShown=0.5,
                lineBreakAfterTag=True,
            ),
            html.Div(
                style={"margin": "10px 0px"},
                children=[
                    html.Div(
                        style={"display": "inline-flex"},
                        children=[
                            wcc.Label("Date:"),
                            wcc.Label(
                                datetime_utils.to_str(dates[-1]),
                                id=self.register_component_unique_id(
                                    self.Ids.DATE_SELECTED_TEXT
                                ),
                                style={"margin-left": "10px"},
                            ),
                            dcc.Store(
                                id=self.register_component_unique_id(
                                    self.Ids.DATE_SELECTED
                                ),
                                storage_type="session",
                                data=datetime_utils.to_str(dates[-1]),
                            ),
                        ],
                    ),
                    wcc.Slider(
                        id=self.register_component_unique_id(self.Ids.DATE_SLIDER),
                        value=len(dates) - 1,
                        min=0,
                        max=len(dates) - 1,
                        step=1,
                        included=False,
                        marks={
                            idx: {
                                "label": datetime_utils.to_str(dates[idx]),
                                "style": {"white-space": "nowrap"},
                            }
                            for idx in [0, len(dates) - 1]
                        },
                    ),
                ],
            ),
            wcc.Dropdown(
                label="Parameter",
                id=self.register_component_unique_id(self.Ids.PARAMETERS),
                options=[
                    {"label": i, "value": i} for i in self._parametermodel.parameters
                ],
                placeholder="Select a parameter...",
                clearable=False,
            ),
        ]
