import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...models import ParametersModel, SimulationTimeSeriesModel
from ._settings import (
    ParamRespOptions,
    ParamRespParameterFilter,
    ParamRespSelections,
    ParamRespVizualisation,
)


class ParameterResponseView(ViewABC):
    class Ids(StrEnum):
        SELECTIONS = "selections"
        VIZUALISATION = "vizualisation"
        OPTIONS = "options"
        PARAMETER_FILTER = "parameter-filter"

    def __init__(
        self,
        parametermodel: ParametersModel,
        vectormodel: SimulationTimeSeriesModel,
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Parameter Response Analysis")

        self._parametermodel = parametermodel
        self._vectormodel = vectormodel
        self._theme = theme

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS: ParamRespSelections(
                    self._parametermodel, self._vectormodel
                ),
                self.Ids.OPTIONS: ParamRespOptions(),
                self.Ids.VIZUALISATION: ParamRespVizualisation(self._theme),
                self.Ids.PARAMETER_FILTER: ParamRespParameterFilter(
                    self._parametermodel.dataframe, self._parametermodel.ensembles
                ),
            }
        )
