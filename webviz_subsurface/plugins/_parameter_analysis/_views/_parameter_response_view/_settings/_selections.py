from typing import List

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dcc, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ......_providers import Frequency
from ...._utils import ParametersModel, ProviderTimeSeriesDataModel
from ...._utils import _datetime_utils as datetime_utils


class ParamRespSelections(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        VECTOR_SELECTOR = "vector-selector"
        DATE_SELECTED_TEXT = "date-selected-text"
        DATE_SELECTED = "date-selected"
        DATE_SLIDER = "date-slider"
        PARAMETER_SELECT = "parameter-select"
        RESAMPLING_FREQUENCY_DROPDOWN = "resampling-frequency-dropdown"

    def __init__(
        self,
        parametermodel: ParametersModel,
        vectormodel: ProviderTimeSeriesDataModel,
        selected_resampling_frequency: Frequency,
        disable_resampling_dropdown: bool,
    ) -> None:
        super().__init__("Selections")
        self._parametermodel = parametermodel
        self._vectormodel = vectormodel
        self._selected_resampling_frequency = selected_resampling_frequency
        self._disable_resampling_dropdown = disable_resampling_dropdown

    def layout(self) -> List[Component]:
        dates = self._vectormodel.dates
        ensembles = self._parametermodel.ensembles
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
                id=self.register_component_unique_id(self.Ids.VECTOR_SELECTOR),
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
                id=self.register_component_unique_id(self.Ids.PARAMETER_SELECT),
                options=[
                    {"label": i, "value": i} for i in self._parametermodel.parameters
                ],
                placeholder="Select a parameter...",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Resampling frequency",
                id=self.register_component_unique_id(
                    self.Ids.RESAMPLING_FREQUENCY_DROPDOWN
                ),
                clearable=False,
                disabled=self._disable_resampling_dropdown,
                options=[
                    {
                        "label": frequency,
                        "value": frequency,
                    }
                    for frequency in Frequency
                ],
                value=self._selected_resampling_frequency,
            ),
        ]
