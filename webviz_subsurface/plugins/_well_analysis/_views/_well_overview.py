from typing import Dict, List, Tuple

import pandas as pd
import plotly.colors
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_wlf_tutorial.plugins.population_analysis.views import population

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .._plugin_ids import PluginIds
from .._view_elements import Graph
from ._settings import OverviewFilter, OverviewPlotSettings


class OverviewView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        BAR_CHART = "bar-chart"
        PLOT_SETTINGS = "plot-settings"
        FILTER = "filter"


    def __init__(self, 
        data_models: Dict[str, EnsembleWellAnalysisData]
    ) -> None:
        super().__init__("Well overview")

        self.data_models = data_models

        self.add_settings_group(OverviewPlotSettings(self.data_models), OverviewView.Ids.PLOT_SETTINGS)
        self.add_settings_group(OverviewFilter(self.data_models), OverviewView.Ids.FILTER)
        