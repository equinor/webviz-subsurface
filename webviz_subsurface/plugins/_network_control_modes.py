from typing import List, Dict, Union, Tuple, Callable

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

from webviz_subsurface._models import EnsembleSetModel
from webviz_subsurface._models import caching_ensemble_set_model_factory

class NetworkControlModes(WebvizPluginABC):
    """Description

    """

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
                column_keys=["WMCTL:*", "GMCT*", "FMCT*" "GPR:*", ]
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.smry_meta = self.emodel.load_smry_meta()
        self.ensembles = list(self.smry["ENSEMBLE"].unique())

        #self.set_callbacks(app)

    # @property
    # def tour_steps(self) -> List[dict]:
    #     return [{}]

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=[
                        html.Span(
                                "Ensemble:", style={"font-weight": "bold"}
                            ),
                        dcc.Dropdown(
                            id=self.uuid("ensemble"),
                            clearable=False,
                            multi=False,
                            options=[
                                {"label": i, "value": i} for i in self.ensembles
                            ],
                            value=[self.ensembles[0]],
                            persistence=True,
                            persistence_type="session",
                        ),
                    ]
                ),
                html.Div(
                    style={"flex": 3},
                    children=wcc.Graph(
                        id=self.uuid("graph"),
                    ),
                )
            ]
        )