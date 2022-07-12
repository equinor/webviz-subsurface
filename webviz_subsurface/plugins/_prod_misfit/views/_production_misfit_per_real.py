from datetime import datetime
from typing import List, Tuple

import pandas as pd
import plotly.colors
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_wlf_tutorial.plugins.population_analysis.views import population

from .._plugin_ids import PluginIds
from ..view_elements import Graph


class MisfitPerRealView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        POPULATION = "population"
    
    def __init__(self, 
        ensemble_names: List[str],
        dates: List[datetime],
        phases: List[str],
        wells: List[str],
        all_well_collection_names: List[str],
        realizations: List[int],
    ) -> None:
        super().__init__("Production misfit per real")
        
        self.ensemble_names = ensemble_names
        self.dates = dates
        self.phases = phases
        self.wells = wells
        self.realizations = realizations
        self.all_well_collection_names = all_well_collection_names

        