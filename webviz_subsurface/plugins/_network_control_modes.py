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
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
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
                column_keys=["WMCTL:*", "GMCT*", "FMCT*", "GPR:*", ]
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent / "_assets" / "css" / "container.css"
        )
        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions: List[Tuple[Callable, list]] = []
        functions.extend(self.emodel.webvizstore)
        return functions

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
                        self.selectors_layout()
                    ]
                ),
                html.Div(
                    className="framed",
                    style={"flex": 3, "height": "89vh"},
                    children=[
                        html.Div(
                            children=wcc.Graph(id=self.uuid("ctrlmode_areachart"))
                        )
                    ]
                )
            ]
        )



    def selectors_layout(self):
        return html.Div(
            className = "framed",
            style={"fontSize": "14"},
            children=[
                dropdown_for_plotly_data(
                    uuid=self.uuid("ensemble_dropdown"),
                    title="Ensemble",
                    options=[{"label": col, "value": col} for col in self.ensembles],
                    value=self.ensembles[0],
                    multi=False,
                ),
                html.Div(
                    id=self.uuid("node_type"),
                    style={"marginTop": "15px"},
                    children=[
                        html.Label(
                            "Node type", style={"backgroundColor": "transparent", "fontWeight": "bold"}
                        ),
                        dcc.RadioItems(
                            id=self.uuid("node_type_radioitems"),
                            className="block-options",
                            options=[
                                {
                                    "label": "Well",
                                    "value": "well",
                                },
                                {
                                    "label": "Field/Group",
                                    "value": "field_group",
                                }
                            ],
                            value="well",
                            persistence=True,
                            persistence_type="session",
                        )
                    ]
                ),
                dropdown_for_plotly_data(
                    uuid=self.uuid("node_dropdown"),
                    title="Node",
                    options=[],
                    value=None,
                    multi=False,
                ),
            ]
        )


    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.uuid("node_dropdown"), "options"),
            Output(self.uuid("node_dropdown"), "value"),
            Input(self.uuid("ensemble_dropdown"), "value"),
            Input(self.uuid("node_type_radioitems"), "value"),
        )
        def _update_node_dropdown(ensemble: str, node_type: str) -> list:
            print("update node dropdown")
            smry = self.smry[self.smry.ENSEMBLE==ensemble].copy()
            smry.dropna(how='all', axis=1, inplace=True)

            if node_type == "well":
                nodes = [vec.split(":")[1] for vec in smry.columns if vec.startswith("WMCTL")]
            elif node_type == "field_group":
                nodes = [vec.split(":")[1] for vec in smry.columns if vec.startswith("GMCTP")]
            else:
                raise ValueError(f"Node type {node_type} not implemented.")
            if not nodes:
                return [], None
            return [{"label": node, "value": node} for node in nodes], nodes[0]

        @app.callback(
            Output(self.uuid("ctrlmode_areachart"), "figure"),
            Input(self.uuid("ensemble_dropdown"), "value"),
            Input(self.uuid("node_type_radioitems"), "value"),
            Input(self.uuid("node_dropdown"), "value"),
        )
        def _make_area_chart(ensemble: str, node_type: str, node: str):
            print("make chart")
            sumvec = f"WMCTL:{node}"
            if not sumvec in self.smry.columns:
                return go.Figure()
            smry = self.smry[self.smry.ENSEMBLE==ensemble][["DATE", sumvec]]
            df = smry.groupby("DATE")[sumvec].value_counts().unstack().fillna(0).reset_index()
            df["Other"] = 0
            categories = get_ctrlmode_categories(node_type)

            fig = go.Figure()

            for col in [col for col in df.columns if not col in ["DATE", "Other"]]:
                if str(col) in categories:
                    name = categories[str(col)]["name"]
                    color = categories[str(col)]["color"]
                    add_trace(fig, df.DATE, df[col], name, color)
                else:
                    df.Other = df.Other + df[col]
            #df.to_csv("plotdata.csv")
            if df.Other.sum()>0:
                add_trace(fig, df.DATE, df.Other, categories["Other"]["name"], categories["Other"]["color"])

            fig.update_layout(
                title_text="Number of realizations on different control modes",
                yaxis_title="# realizations",
                margin=dict(t=60),
                yaxis=dict(range=[0,self.smry.REAL.nunique()]),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig

def add_trace(fig, x_series, y_series, name, color):
    """Description"""
    fig.add_trace(
        go.Scatter(
            x=x_series,
            y=y_series,
            hoverinfo="x+y",
            mode="lines",
            line=dict(width=0.5, color=color),
            name=name,
            stackgroup="one",
        )
    )

# pylint: disable=too-many-arguments
def dropdown_for_plotly_data(
    uuid: str,
    title: str,
    options: List[Dict],
    value: Union[List, str] = None,
    flex: int = 1,
    placeholder: str = "Select...",
    multi: bool = False,
    clearable: bool = False,
) -> html.Div:
    return html.Div(
        style={"flex": flex},
        children=[
            html.Label(
                title, style={"backgroundColor": "transparent", "fontWeight": "bold"}
            ),
            dcc.Dropdown(
                style={"backgroundColor": "transparent"},
                id=uuid,
                options=options,
                value=value,
                clearable=clearable,
                placeholder=placeholder,
                multi=multi,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def get_ctrlmode_categories(node_type):
    """Description"""
    return {
        "0.0":{
            "name": "SHUT/STOP",
            "color": "#302f2f" #grey
        },
        "1.0":{
            "name": "ORAT",
            "color": "#044a2e" #green
        },
        "2.0":{
            "name": "WRAT",
            "color": "#10026b" #blue
        },
        "3.0":{
            "name": "GRAT",
            "color": "#7a0202" #red
        },
        "4.0":{
            "name": "LRAT",
            "color": "#b06d15" #muted purple
        },
        "5.0":{
            "name": "RESV",
            "color": "#67ab99" #green/blue
        },
        "6.0":{
            "name": "THP",
            "color": "#7e5980" #purple
        },
        "7.0":{
            "name": "BHP",
            "color": "#1f77b4" #muted blue
        },
        "-1.0":{
            "name": "GRUP",
            "color": "#cfcc74" #yellow
        },
        "Other":{
            "name": "Other",
            "color": "#ffffff" #white
        }
    }