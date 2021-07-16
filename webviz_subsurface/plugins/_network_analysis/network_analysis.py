from typing import List, Dict, Union, Tuple, Callable
from pathlib import Path

import plotly.graph_objects as go
import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, EncodedFile
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

import webviz_subsurface
from webviz_subsurface._models import EnsembleSetModel
from webviz_subsurface._models import caching_ensemble_set_model_factory

from .views import main_view
from .controllers import selections_controllers

class NetworkAnalysis(WebvizPluginABC):
    """Description"""

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        sampling: str = "monthly",
    ):

        super().__init__()
        self.time_index = sampling
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.emodel: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                },
                time_index=self.time_index,
                column_keys=[
                    "WMCTL:*",
                    "GMCT*",
                    "FMCT*",
                    "WTHP:*",
                    "WBHP:*",
                    "GPR:*",
                    "FPR",
                ],
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.theme = webviz_settings.theme

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions: List[Tuple[Callable, list]] = []
        functions.extend(self.emodel.webvizstore)
        return functions

    # @property
    # def tour_steps(self) -> List[dict]:
    #     return [{}]

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                #clientside_stores(get_uuid=self.uuid),
                main_view(
                    get_uuid=self.uuid,
                    theme=self.theme,
                    ensembles=self.ensembles
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        selections_controllers(app=app, get_uuid=self.uuid, smry=self.smry)
