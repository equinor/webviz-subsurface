import json
import pandas as pd
import numpy as np
import random

import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface_components
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings

from .._datainput.fmu_input import load_csv

class WellCompletions(WebvizPluginABC):
    """
    Description goes here
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        compdatfile: str = "share/results/wells/compdat.csv"
    ):
        super().__init__()

        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        #print(self.ens_paths)
        self.compdat = load_csv(ensemble_paths=self.ens_paths, csv_file=compdatfile)

        self.set_callbacks(app)

    # def add_webvizstore(self):
    #     return (
    #         [
    #             (
    #                 create_ensemble_dataset,
    #                 [
    #                     {"compdat":self.compdat[self.compdat.ENSEMBLE==ensemble]}
    #                     for ens in ensembles
    #                 ],
    #             )
    #         ]
    #     )



    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    children=[
                        html.Div(
                            children=html.Label(
                                children=[
                                    html.Span("Ensemble", style={"font-weight": "bold"}),
                                    dcc.Dropdown(
                                        id=self.uuid("ensemble_dropdown"),
                                        options=[
                                            {"label": i, "value": i}
                                            for i in list(self.compdat.ENSEMBLE.unique())
                                        ],
                                        clearable=False,
                                        value=list(self.compdat.ENSEMBLE.unique())[0],
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ]
                            ),
                        )
                    ],
                ),
                html.Div(
                    id=self.uuid("well_completions_wrapper"),
                    style={"height":600},
                )
            ]
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            [
                Output(self.uuid("well_completions_wrapper"), "children"),
            ],
            [Input(self.uuid("ensemble_dropdown"), "value")]
        )
        def _render_well_completions(ensemble_name):
            data = self.create_ensemble_dataset(ensemble_name)
            return [
                webviz_subsurface_components.WellCompletions(id="well_completions", data=data)
            ]

    #@CACHE.memoize(timeout=CACHE.TIMEOUT)
    #@webvizstore
    def create_ensemble_dataset(self, ensemble):

        """
        Create the well completion data appropriate for the WellCompletions component in the correct format
        """
        df = self.compdat[self.compdat.ENSEMBLE==ensemble]

        time_steps = sorted(df.DATE.unique())
        realisations = np.asarray(sorted(df.REAL.unique()), dtype=np.int32)
        layers = np.sort(df.K1.unique())

        result = {}
        result["stratigraphy"] = extract_stratigraphy(layers)
        result["time_steps"] = time_steps

        zone_names = [a["name"] for a in result["stratigraphy"]]
        result["wells"] = extract_wells(df, layers, zone_names, time_steps, realisations)

        with open("/private/olind/webviz/result.json", "w") as fp:
            json.dump(result, fp)

        fn = "/private/olind/webviz/well-completions-with-attr.json"
        with open(fn, "r") as json_file:
            data = json.load(json_file)
        return data


def extract_well(df, well, layers, zone_names, time_steps, realisations):
    """
    Extract completion data for a single well
    """
    well_dict = {}
    return well_dict

def extract_wells(df, layers, zone_names, time_steps, realisations):
    """
    Generates the wells part of the input dictionary to the WellCompletions component
    """
    well_list = []
    for name, well_group in df.groupby("WELL"):
        well_list.append(
            extract_well(well_group, name, layers, zone_names, time_steps, realisations)
        )
    return well_list

def random_color_str():
    r = random.randint(8, 15)  # nosec - bandit B311
    g = random.randint(8, 15)  # nosec - bandit B311
    b = random.randint(8, 15)  # nosec - bandit B311
    s = hex((r << 8) + (g << 4) + b)
    return "#" + s[-3:]

def extract_stratigraphy(layers):
    result = []
    for layer in layers:
        zdict = {}
        zdict["name"] = "zone" + str(layer)
        zdict["color"] = random_color_str()
        result.append(zdict)
    return result
