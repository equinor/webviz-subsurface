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

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from ..._utils import SimulationTimeSeriesOneByOneDataModel
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

    def __init__(self, data_model: SimulationTimeSeriesOneByOneDataModel) -> None:
        super().__init__("OneByOne View")
        self._data_model = data_model

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS: Selections(
                    ensembles=self._data_model.ensembles,
                    vectors=self._data_model._vectors,
                    dates=self._data_model.dates,
                )
            }
        )
