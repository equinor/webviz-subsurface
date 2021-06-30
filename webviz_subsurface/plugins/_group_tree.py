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
from .._datainput.fmu_input import load_csv

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
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Selectors(
                            label="Ensemble",
                            children=[
                                wcc.Dropdown(
                                    id=self.uuid("ensemble_dropdown"),
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    clearable=False,
                                    value=self.ensembles[0],
                                ),
                            ],
                        ),
                        html.Div(style={"flex": 4}),
                    ],
                ),
                html.Div(
                    id=self.uuid("grouptree_wrapper"),
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.uuid("grouptree_wrapper"), "children"),
            Output(self.uuid("grouptree_wrapper"), "style"),
            Input(self.uuid("ensemble_dropdown"), "value"),
        )
        def _render_grouptree(ensemble_name: str) -> list:

            data = json.load(
                create_ensemble_dataset(
                    ensemble_name,
                    self.ens_paths[ensemble_name],
                    self.gruptree_file,
                    self.time_index,
                )
            )
            return [
                webviz_subsurface_components.GroupTree(id="grouptree", data=data),
                {"padding": "10px"},
            ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def create_ensemble_dataset(
    ensemble: str,
    ensemble_path: str,
    gruptree_file: str,
    time_index: str,
) -> io.BytesIO:
    """Description"""
    print("Lager datasett ...")

    smry = load_smry(ensemble, ensemble_path, time_index)
    df_gruptrees = load_csv(
        ensemble_paths={ensemble: ensemble_path}, csv_file=gruptree_file
    )
    df_gruptrees.DATE = pd.to_datetime(df_gruptrees.DATE).dt.date
    #smry.DATE = pd.to_datetime(smry.DATE).dt.date
    trees = []

    # loop trees
    for tree_date, df_gruptree in df_gruptrees.groupby("DATE"):
        next_tree_date = df_gruptrees[df_gruptrees.DATE>tree_date].DATE.min()
        if pd.isna(next_tree_date):
            next_tree_date = smry.DATE.max()
        smry_in_datespan = smry[(smry.DATE>=tree_date) & (smry.DATE<next_tree_date)]
        dates = list(smry_in_datespan.DATE.unique())
        # str_dates = [date.strftime("%Y-%m-%d") for date in dates]
        # print(
        #     f"from date: {tree_date} "
        #     f"next_date: {next_tree_date} "
        #     f"dates: {str_dates} "
        # )
        trees.append(
            {
                "dates": [date.strftime("%Y-%m-%d") for date in dates],
                "tree": extract_tree(df_gruptree, "FIELD", smry_in_datespan, dates)
            }

        )

    with open(f"/private/olind/webviz/grouptree_suggested_format_{ensemble}.json", "w") as handle:
        json.dump(trees, handle)
        print("output exported")

    return io.BytesIO(json.dumps(trees).encode())


def extract_tree(df_gruptree, node, smry_in_datespan, dates) -> dict:
    """Description"""
    node_type = df_gruptree[df_gruptree.CHILD == node].KEYWORD.iloc[0]
    node_values = get_node_smry(node, node_type, smry_in_datespan, dates)
    result = {
        "name": node,
        "pressure": node_values["pressure"],
        "oilrate": node_values["oilrate"],
        "waterrate": node_values["waterrate"],
        "gasrate": node_values["gasrate"],
        "grupnet": "Grupnet info",
    }
    children = list(df_gruptree[df_gruptree.PARENT == node].CHILD.unique())
    if children:
        result["children"] = [
            extract_tree(df_gruptree, child_node, smry_in_datespan, dates)
            for child_node in df_gruptree[df_gruptree.PARENT == node].CHILD.unique()
        ]
    return result


def get_node_smry(node, node_type, smry_in_datespan, dates) -> pd.DataFrame:
    """Description"""
    if node == "FIELD":
        sumvecs = {
            "oilrate": "FOPR",
            "gasrate": "FGPR",
            "waterrate": "FWPR",
            "pressure": "FPR",
        }
    elif node_type == "GRUPTREE":
        sumvecs = {
            "oilrate": f"GOPR:{node}",
            "gasrate": f"GGPR:{node}",
            "waterrate": f"GWPR:{node}",
            "pressure": f"GPR:{node}",
        }
    elif node_type == "WELSPECS":
        sumvecs = {
            "oilrate": f"WOPR:{node}",
            "gasrate": f"WGPR:{node}",
            "waterrate": f"WWPR:{node}",
            "pressure": f"WTHP:{node}",
        }
    for sumvec in sumvecs.values():
        if sumvec not in smry_in_datespan.columns:
            smry_in_datespan[sumvec] = np.nan

    output = {"pressure":[], "oilrate":[], "waterrate":[], "gasrate":[]}
    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE==date]
        smry_mean = smry_at_date[sumvecs.values()].mean()
        for key in sumvecs:
            output[key].append(round(smry_mean.loc[sumvec],2))
    return output


def load_smry(ensemble: str, ensemble_path: str, time_index: str) -> pd.DataFrame:
    """Description"""

    emodel: EnsembleSetModel = caching_ensemble_set_model_factory.get_or_create_model(
        ensemble_paths={ensemble: ensemble_path},
        time_index=time_index,
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
    return emodel.get_or_load_smry_cached()
