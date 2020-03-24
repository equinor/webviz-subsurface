import os
from uuid import uuid4

import pandas as pd
from pathlib import Path
import colorlover as cl
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC


class Rft(WebvizPluginABC):
    def __init__(self, app, formations: Path, simulations: Path, observations: Path):
        super().__init__()
        self.formations = formations
        self.simulations = simulations
        self.observations = observations

        self.formationdf = pd.read_csv(self.formations, comment="#")
        self.simdf = pd.read_csv(self.simulations)
        self.obsdf = pd.read_csv(self.observations)
        self.set_callbacks(app)

    @property
    def well_names(self):
        return list(self.obsdf["WELL"].unique())

    def dates(self, well):
        df = self.obsdf.loc[self.obsdf["WELL"] == well]
        return list(df["DATE"].unique())

    @property
    def ensembles(self):
        return list(self.simdf["ENSEMBLE"].unique())

    @property
    def formation_colors(self):
        return cl.interp(
            cl.scales["8"]["qual"]["Pastel2"], len(self.formationdf["FM"].unique())
        )

    def observed_plot(self, well, date):
        """Plot observed pressure as points"""
        df = self.obsdf.loc[self.obsdf["WELL"] == well]
        df = df.loc[df["DATE"] == date]
        return {
            "x": df["PRESSURE"],
            "y": df["DEPTH"],
            "type": "scatter",
            "mode": "markers",
            "name": "observed",
            "marker": {"color": "black", "size": 3},
        }

    def simulated_plot(self, well, date, ensemble):
        """Plot simulated pressure per realization as lines"""
        df = self.simdf.loc[self.simdf["WELL"] == well]
        df = df.loc[df["DATE"] == date]
        df = df.loc[df["ENSEMBLE"] == ensemble]
        traces = []
        for real, realdf in df.groupby("REAL"):
            traces.append(
                {
                    "x": realdf["PRESSURE"],
                    "y": realdf["DEPTH"],
                    "type": "scatter",
                    "mode": "line",
                    "name": "simulated",
                    "showlegend": False,
                    # "line": {"color": p_colors[real], "width": 3},
                }
            )
        return traces

    def formation_plot(self, well):
        """Plot zonation"""
        df = self.formationdf.loc[self.formationdf["WELL"] == well]
        traces = []
        names = []
        for i, (index, row) in enumerate(df.iterrows()):
            traces.append(
                {
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "name": row["FM"],
                    "y0": row["TOP_TVD"],
                    "y1": row["BTM_TVD"],
                    "linecolor": self.formation_colors[i],
                    "fillcolor": self.formation_colors[i],
                    "type": "rect",
                    "layer": "below",
                    # "line_width":0,
                }
            )
            names.append(
                {
                    "showlegend": False,
                    "type": "scatter",
                    "y": [(row["BTM_TVD"] + row["TOP_TVD"]) / 2],
                    # "xref": "paper",
                    # "x": [1],
                    "text": row["FM"],
                    "mode": "text",
                }
            )
        traces.pop()
        return traces, names

    @property
    def layout(self):

        return html.Div(
            children=[
                dcc.Dropdown(
                    id=self.uuid("well"),
                    options=[
                        {"label": well, "value": well} for well in self.well_names
                    ],
                    value=self.well_names[0],
                ),
                dcc.Dropdown(
                    id=self.uuid("date"),
                    options=[{"label": date, "value": date} for date in self.dates(self.well_names[0])],
                    value=self.dates(self.well_names[0])[0],
                ),
                dcc.Dropdown(
                    id=self.uuid("ensemble"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=self.ensembles[0],
                ),
                dcc.Graph(id=self.uuid("graph"),),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("well"), "value"),
                Input(self.uuid("date"), "value"),
                Input(self.uuid("ensemble"), "value"),
            ],
        )
        def update_well(well, date, ensemble):
            obsplot = [self.observed_plot(well, date)]
            simplot = self.simulated_plot(well, date, ensemble)
            zon_shapes, zon_names = self.formation_plot(well)
            plot_layout = {
                "yaxis": {"autorange": "reversed", "title": "Depth"},
                "xaxis": {"title": "Pressure"},
                "height": 800,
                "margin": {"t": 50},
                "shapes": zon_shapes,
            }
            return {
                "data": simplot + obsplot,
                "layout": plot_layout,
            }

        @app.callback(
            [Output(self.uuid("date"), "options"), Output(self.uuid("date"), "value")],
            [Input(self.uuid("well"), "value"),],
            [State(self.uuid("date"), "value")],
        )
        def update_date(well, current_date):
            dates = self.dates(well)
            available_dates = [{'label':date, 'value':date} for date in dates]
            date = current_date if current_date in dates else dates[0]
            return available_dates, date
            
