from typing import Optional, List, Dict, Tuple, Callable, Any, Iterator
import json
import io

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output
import dash_html_components as html

from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_subsurface_components
import webviz_core_components as wcc

from webviz_subsurface._models import EnsembleSetModel
from webviz_subsurface._models import caching_ensemble_set_model_factory
from .controllers import controllers
from .views import main_view

"""
Notater:
- hvordan handtere realisasjoner
- hvordan handtere historikk vs sim data
- GPR maa legges til Drogon
- well attributes filter i frontend
- Hva med BHP? egen node eller data pa bronnode
- Naar tre og data skal skilles, hvordan haandteres manglende verdier i data? frontend eller backend?
- Maa kunne velge rate istedetfor grupnet info
"""


class GroupTree(WebvizPluginABC):
    """Documentation"""

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        time_index: str = "monthly",
    ):
        super().__init__()
        self.ensembles = ensembles
        self.gruptree_file = gruptree_file
        self.time_index = time_index

        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.set_callbacks(app)

    # def add_webvizstore()

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                # clientside_stores(get_uuid=self.uuid),
                main_view(get_uuid=self.uuid, ensembles=self.ensembles),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controllers(
            app=app,
            get_uuid=self.uuid,
            ens_paths=self.ens_paths,
            gruptree_file=self.gruptree_file,
            time_index=self.time_index,
        )
