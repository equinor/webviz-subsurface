import warnings
from pathlib import Path
from typing import Optional, Type, Union

import pandas as pd
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface

from ..._datainput.fmu_input import load_csv
from ._error import error
from ._plugin_ids import PlugInIDs


class ParameterCorrelation(WebvizPluginABC):
    """Descibtion of plugin"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        drop_constants: bool = True,
    ) -> None:
        super().__init__()

        self.error_message = ""
        self.ensembles = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.drop_constants = drop_constants
        self.plotly_theme = webviz_settings.theme.plotly_theme

    @property
    def p_cols(self) -> list:
        dfs = [
            get_corr_data(ens, self.drop_constants) for ens in self.ensembles.values()
        ]
        return sorted(list(pd.concat(dfs, sort=True).columns))

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)
