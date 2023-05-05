import datetime
from typing import Dict, List, Optional, Tuple, Union

import dash
import pandas as pd
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile, WebvizPluginABC
from webviz_config._theme_class import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._models.parameter_model import ParametersModel

from ._settings import Selections

class OneByOneView(ViewABC):
    class Ids(StrEnum):
        TIMESERIES_PLOT = "time-series-plot"
        TORNADO_PLOT = "tornado-plot"
        DATA_TABLE = "data-table"

        SELECTIONS = "selections"
        VIZUALISATION = "vizualisation"
        SENSITIVITY_FILTER = "sensitivity-filter"
        SETTINGS = "settings"

    def __init__(
            self,
            provider_set: Dict[str, EnsembleSummaryProvider],
            parameter_model: ParametersModel,
    ) -> None:
        super().__init__("OneByOne View")
        self._provider_set = provider_set
        self._parameter_model = parameter_model

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS : Selections(
                    ensembles=list(self._provider_set.keys()),
                    vectors=[],
                    dates=[],
                )
            }
        )
