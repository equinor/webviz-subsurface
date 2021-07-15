from typing import List, Dict, Union, Tuple, Callable
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
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
                    "GPR:*",
                ],
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "container.css"
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
                wcc.FlexColumn(
                    flex=1, style={"height": "90vh"}, children=[self.selectors_layout()]
                ),
                wcc.FlexColumn(
                    flex=4,
                    children=[
                        wcc.Frame(
                            style={"height": "90vh"},
                            highlight=False,
                            color="white",
                            children=wcc.Graph(
                                style={"height": "85vh"}, id=self.uuid("graph")
                            ),
                        )
                    ],
                ),
            ],
        )

    def selectors_layout(self):
        return html.Div(
            className="framed",
            style={"fontSize": "14"},
            children=[
                wcc.Selectors(
                    label="Ensemble",
                    children=wcc.Dropdown(
                        id=self.uuid("ensemble_dropdown"),
                        options=[
                            {"label": col, "value": col} for col in self.ensembles
                        ],
                        value=self.ensembles[0],
                        multi=False,
                    ),
                ),
                wcc.Selectors(
                    label="Node type:",
                    children=wcc.RadioItems(
                        id=self.uuid("node_type_radioitems"),
                        options=[
                            {
                                "label": "Well",
                                "value": "well",
                            },
                            {
                                "label": "Field/group",
                                "value": "field_group",
                            },
                        ],
                        value="well",
                    ),
                ),
                wcc.Selectors(
                    label="Node",
                    children=wcc.Dropdown(
                        id=self.uuid("node_dropdown"),
                        options=[],
                        value=None,
                        multi=False,
                    ),
                ),
            ],
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
            smry = self.smry[self.smry.ENSEMBLE == ensemble].copy()
            smry.dropna(how="all", axis=1, inplace=True)

            if node_type == "well":
                nodes = [
                    vec.split(":")[1] for vec in smry.columns if vec.startswith("WMCTL")
                ]
            elif node_type == "field_group":
                nodes = [
                    vec.split(":")[1] for vec in smry.columns if vec.startswith("GMCTP")
                ] + ["FIELD"]
            else:
                raise ValueError(f"Node type {node_type} not implemented.")
            if not nodes:
                return [], None
            return [{"label": node, "value": node} for node in nodes], nodes[0]

        @app.callback(
            Output(self.uuid("graph"), "figure"),
            Input(self.uuid("ensemble_dropdown"), "value"),
            Input(self.uuid("node_type_radioitems"), "value"),
            Input(self.uuid("node_dropdown"), "value"),
        )
        def _update_graph(ensemble: str, node_type: str, node: str):
            print("make chart")

            if ensemble is None or node_type is None or node is None:
                # Format this a bit more
                return go.Figure()

            fig = make_subplots(
                rows=2,
                shared_xaxes=False,
                vertical_spacing=0.05,
                subplot_titles=[
                    "Number of realizations on different control modes",
                    "Node pressures",
                ],
            )

            fig.add_traces(
                [
                    make_area_chart(ensemble, node_type, node, self.smry),
                    make_node_pressure_graph(),
                ],
                rows=[1, 2],
            )

            return fig


def make_node_pressure_graph():
    """Description"""
    return go.Figure()


def make_area_chart(ensemble: str, node_type: str, node: str, smry: pd.DataFrame):
    """Description"""

    ctrl_mode_sumvec = sumvec = get_sumvec_from_nodetype_and_name(node_type, node)
    sumvec = get_sumvec_from_nodetype_and_name(node_type, node)
    fig = go.Figure
    if not sumvec in smry.columns:
        print(f"{sumvec} not in emsemble")
        return fig

    smry = smry[smry.ENSEMBLE == ensemble][["DATE", sumvec, "REAL"]]
    df = smry.groupby("DATE")[sumvec].value_counts().unstack().fillna(0).reset_index()
    return px.area(smry, x="DATE", y=sumvec, color="REAL")
    # df["Other"] = 0
    # categories = get_ctrlmode_categories(node_type)

    # for col in [col for col in df.columns if not col in ["DATE", "Other"]]:
    #     if str(col) in categories:
    #         name = categories[str(col)]["name"]
    #         color = categories[str(col)]["color"]
    #         #add_trace(fig, df.DATE, df[col], name, color)
    #     else:
    #         df.Other = df.Other + df[col]

    # if df.Other.sum()>0:
    #    add_trace(fig, df.DATE, df.Other, categories["Other"]["name"], categories["Other"]["color"])

    # fig.update_layout(
    #     title_text="Number of realizations on different control modes",
    #     yaxis_title="# realizations",
    #     margin=dict(t=60),
    #     yaxis=dict(range=[0,self.smry.REAL.nunique()]),
    #     paper_bgcolor="rgba(0,0,0,0)",
    #     plot_bgcolor="rgba(0,0,0,0)",
    # )

    # return fig


def get_sumvec_from_nodetype_and_name(node_type: str, node: str):
    """Description"""
    if node is None:
        return None
    elif node == "FIELD":
        return "FMCTP"
    elif node_type == "well":
        return f"WMCTL:{node}"
    elif node_type == "field_group":
        return f"GMCTP:{node}"
    else:
        raise ValueError(f"Node type {node_type} not implemented")


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


def get_ctrlmode_categories(node_type):
    """Description"""
    if node_type == "well":
        return {
            "0.0": {"name": "SHUT/STOP", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": "#044a2e"},  # green
            "2.0": {"name": "WRAT", "color": "#10026b"},  # blue
            "3.0": {"name": "GRAT", "color": "#7a0202"},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "THP", "color": "#7e5980"},  # purple
            "7.0": {"name": "BHP", "color": "#1f77b4"},  # muted blue
            "-1.0": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    elif node_type == "field_group":
        return {
            "0.0": {"name": "NONE", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": "#044a2e"},  # green
            "2.0": {"name": "WRAT", "color": "#10026b"},  # blue
            "3.0": {"name": "GRAT", "color": "#7a0202"},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "PRBL", "color": "#7e5980"},  # purple
            "7.0": {"name": "ENERGY", "color": "#1f77b4"},  # muted blue
            "-ve": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    else:
        raise ValueError(f"Node type: {node_type} not implemented")
