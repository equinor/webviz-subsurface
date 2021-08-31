from typing import Optional, List, Dict, Tuple, Callable, Any, Iterator
import json
import io
import glob

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

from ..._models import EnsembleSetModel
from ..._models import caching_ensemble_set_model_factory
from ..._datainput.fmu_input import load_csv
from .controllers import controllers
from .views import main_view

"""
Notater:
- Hva hvis treet ikke er likt over realisasjoner
    - for realisasjon burde man kanskje bruke gruptree-fil fra samme realisasjon
- hvordan handtere historikk vs sim data
- hvordan haandteres manglende verdier i data? Nå sendes NaN verdier
    - frontend eller backend?
- mean av producing real
- warning hvis summary-vektoren mangler? kan bli mange warnings
- hvordan haandtere wefac/gefac ?

Til diskusjon om komponenten:
- Hva med BHP? egen node eller data pa bronnode
- well attributes filter i frontend ?
- Hva med at man kan velge å vise rate som tall istedet for info
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

        self.emodel: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                },
                time_index=self.time_index,
                column_keys=[
                    "FOPR",
                    "FGPR",
                    "FWPR",
                    "FWIR",
                    "FPR",
                    "GOPR:*",
                    "GGPR:*",
                    "GWPR:*",
                    "GPR:*",
                    "WOPR:*",
                    "WGPR:*",
                    "WWPR:*",
                    "WTHP:*",
                    "WBHP:*",
                ],
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.gruptree = read_gruptree_files(self.ens_paths, self.gruptree_file)
        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        functions: List[Tuple[Callable, List[Dict]]] = self.emodel.webvizstore
        functions.append(
            (
                read_gruptree_files,
                [{"ens_paths": self.ens_paths, "gruptree_file": self.gruptree_file}],
            )
        )
        return functions

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
            smry=self.smry,
            gruptree=self.gruptree,
        )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_gruptree_files(ens_paths: Dict[str, str], gruptree_file: str) -> pd.DataFrame:
    """Searches for gruptree files on the scratch disk. These
    files can be exported in the FMU workflow using the ECL2CSV
    forward job with subcommand gruptree
    If one file is found per ensemble this file is assumed to be
    valid for the whole ensemble.
    If BRANPROP is in the KEYWORDS, GRUPTREE rows are filtered out
    """
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        for filename in glob.glob(f"{ens_path}/{gruptree_file}"):
            df_ens = pd.read_csv(filename)
            df_ens["ENSEMBLE"] = ens_name
            if "BRANPROP" in df_ens.KEYWORD.unique():
                df_ens = df_ens[df_ens.KEYWORD != "GRUPTREE"]
            df = pd.concat([df, df_ens])
            break
    df = df.where(pd.notnull(df), None)
    return df
