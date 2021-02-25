from typing import Optional, List, Tuple, Callable
from pathlib import Path

import pandas as pd
import dash
import dash_html_components as html
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from fmu.ensemble import ScratchEnsemble

from webviz_subsurface._models.table_model import EnsembleTableModelSet
from .views import main_view
from .controllers import main_controller


class TablePlotterFMU(WebvizPluginABC):
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensembles: list = None,
        aggregated_csvfile: Path = None,
    ):
        super().__init__()
        if ensembles is not None and csvfile is not None:
            raise ValueError
        elif aggregated_csvfile is not None:
            self.tablemodel = EnsembleTableModelSet.from_aggregated_csv_file(
                aggregated_csvfile
            )
        else:
            raise ValueError(
                "Specify either ensemble and csvfile or aggregated_csvfile"
            )
        self.set_callbacks(app)

    @property
    def layout(self):
        return main_view(parent=self)

    def set_callbacks(self, app):
        return main_controller(parent=self, app=app)