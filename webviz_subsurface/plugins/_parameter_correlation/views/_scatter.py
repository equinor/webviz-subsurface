from typing import List

import numpy as np
import pandas as pd
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from ..view_elements import Graph


class ScatterPlot(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SCATTERPLOT = "scatterplot"

    def __init__(self, ensembles: dict, p_cols: List) -> None:
        super().__init__("Scatter plot")

        self.ensembles = ensembles
        self.p_cols = p_cols

        column = self.add_column()
        first_row = column.add_row()
        first_row.add_view_element(Graph(), ScatterPlot.IDs.SCATTERPLOT)
