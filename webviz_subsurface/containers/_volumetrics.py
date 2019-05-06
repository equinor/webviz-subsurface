from uuid import uuid4
import os
import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import dash_table
from dash.dependencies import Input, Output
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore

class Volumetrics:
    '''### Volumetrics

This container visualizes RMS in-place volumetrics results

* `ensembles`: Which ensembles in `container_settings` to visualize.
* `volfile`:  Local realization path to the RMS volumetrics file
* `title`: Optional title for the container.
'''

    def __init__(self, app, container_settings, ensembles: list, volfile: str,
                 title: str = 'Volumetrics'):

        self.title = title
        self.ensemble_names = ensembles
        self.ensemble_paths = tuple(
            (ens,
             container_settings['scratch_ensembles'][ens])
             for ens in ensembles)

        self.volume_dfs = pd.concat(
            [pd.read_csv(ensemble_path + volfile)
             for ensemble_path in self.ensemble_paths])
        
        print(self.volume_dfs)