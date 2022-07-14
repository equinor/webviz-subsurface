from typing import List, Tuple

import pandas as pd
import plotly.colors
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_wlf_tutorial.plugins.population_analysis.views import population

from .._plugin_ids import PluginIds
from .._view_elements import Graph
from ._settings import OverviewSettings


class OverviewView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        BAR_CHART = "bar-chart"

    def __init__(self, ) -> None:
        super().__init__("Well overview")

        self.add_settings_group()
        