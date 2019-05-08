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
from ..datainput import scratch_ensemble

class Volumetrics:
    """
    ### Volumetrics



    """
    print('init Volumetrics =================================================')
    def __init__(self,
                 app,
                 container_settings,
                 ensembles: list,
                 volfile: str,
                 title: str = 'Volumetrics'):

        self.title = title
        self.ensemble_names = ensembles
        self.ensemble_paths = tuple(
            (ens,
             container_settings['scratch_ensembles'][ens])
             for ens in ensembles)
        print('self.ensemble_paths: ', self.ensemble_paths)
        print('volfile: ', volfile)

        ensemble_dfs = []
        for ens, path in self.ensemble_paths:
            ensemble_i_df = scratch_ensemble(ens, path).load_csv(volfile)
            ensemble_i_df['ENSEMBLE'] = ens
            ensemble_dfs.append(ensemble_i_df)
        self.volume_dfs = pd.concat(ensemble_dfs)


        print('concated dataframe dtypes: ', self.volume_dfs.dtypes)
        print('concated dataframe shape: ', self.volume_dfs.shape)
