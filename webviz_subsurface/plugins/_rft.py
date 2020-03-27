import os
from uuid import uuid4

import pandas as pd
from pathlib import Path
import colorlover as cl
import plotly.express as px
import dash_html_components as html
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC


class Rft(WebvizPluginABC):
    def __init__(
        self,
        app,
        ertdata: Path,
        formations: Path,
        simulations: Path,
        observations: Path,
    ):
        super().__init__()
        self.ertdata = ertdata
        self.formations = formations
        self.simulations = simulations
        self.observations = observations
        self.ertdatadf = pd.read_csv(self.ertdata)
        self.ertagg = df = (
            self.ertdatadf.groupby(["WELL", "DATE", "ENSEMBLE"])
            .aggregate("mean")
            .reset_index()
        )
        print(self.ertagg["ENSEMBLE"])
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
            "marker": {"color": "black", "size": 30},
        }

    def simulated_stat(self, well, date, ensemble, color):
        df = self.simdf.loc[self.simdf["WELL"] == well]
        df = df.loc[df["DATE"] == date]
        df = df.loc[df["ENSEMBLE"] == ensemble]

        quantiles = [10, 90]
        traces = []

        dframe = df.drop(columns=["ENSEMBLE", "REAL"]).groupby("DEPTH")

        # Build a dictionary of dataframes to be concatenated
        dframes = {}
        dframes["mean"] = dframe.mean()
        for quantile in quantiles:
            quantile_str = "p" + str(quantile)
            dframes[quantile_str] = dframe.quantile(q=quantile / 100.0)
        dframes["maximum"] = dframe.max()
        dframes["minimum"] = dframe.min()
        traces.extend(
            add_fanchart_traces(
                pd.concat(dframes, names=["STATISTIC"], sort=False)["PRESSURE"],
                color,
                ensemble,
            )
        )
        return traces

    def simulated_plot(self, well, date, ensemble, color):
        """Plot simulated pressure per realization as lines"""
        df = self.simdf.loc[self.simdf["WELL"] == well]
        df = df.loc[df["DATE"] == date]
        df = df.loc[df["ENSEMBLE"] == ensemble]
        traces = []
        for i, (real, realdf) in enumerate(df.groupby("REAL")):
            traces.append(
                {
                    "x": realdf["PRESSURE"],
                    "y": realdf["DEPTH"],
                    "type": "scatter",
                    "mode": "line",
                    "line": {"color": color},
                    "name": ensemble,
                    "showlegend": i == 0,
                    "legendgroup": ensemble
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
                    "xref": "x",
                    "x": [750],
                    "text": row["FM"],
                    "mode": "text",
                    "line_width": 0,
                }
            )
        traces.pop()
        return traces, names

    def map_plot(self, ensemble):
        df_all = self.ertagg.loc[self.ertagg["ENSEMBLE"] == ensemble]
        df = df_all.loc[df_all['DATE'] == df_all['DATE'].unique()[0]]
        return {
            "data": [
                {
                    "x": df["EAST"],
                    "y": df["NORTH"],
                    "text": df["WELL"],
                    "mode": "markers",
                    "marker": {
                        "size": df["DIFF"],
                        "sizeref": 2.0 * df["DIFF"].max() / (40 ** 2),
                        "sizemode": "area",
                        "color": df["DATE"],
                    },
                }
            ],
            "layout": {
                "height": 800,
                "margin": {"t": 50},
                "xaxis": {"constrain": "domain", "showgrid": False},
                "yaxis": {"scaleanchor": "x", "showgrid": False},

            },
            # "frames":[dict(data=[dict(x=[xx[k]],
            #             y=[yy[k]],
            #             mode='markers',
            #             marker=dict(color='red', size=10)
            #             )
            #       ]) for k in range(N)]
        }

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
                dcc.RadioItems(
                    id=self.uuid("date"),
                    options=[
                        {"label": date, "value": date}
                        for date in self.dates(self.well_names[0])
                    ],
                    labelStyle={'display': 'inline-block',
                                          'margin': '5px'},
                    value=self.dates(self.well_names[0])[0],
                ),
                dcc.Dropdown(
                    id=self.uuid("ensemble"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=self.ensembles[0],
                    multi=True,
                ),
                dcc.RadioItems(
                    id=self.uuid("linetype"),
                    options=[
                        {"label": "Plot realization", "value": "realization"},
                        {"label": "Plot min/max", "value": "fanchart"},
                    ],
                    value="realization",
                ),
                wcc.FlexBox(
                    children=[
                        dcc.Graph(
                            style={"width": "50%"},
                            id=self.uuid("map"),
                            figure=self.map_plot("case1"),
                        ),
                        dcc.Graph(style={"width": "50%"}, id=self.uuid("graph"),),
                    ]
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("well"), "value"), [Input(self.uuid("map"), "clickData"),],
        )
        def get_well(clickData):
            well = clickData["points"][0]["text"]
            print(well)
            return well
            # raise PreventUpdate

        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("well"), "value"),
                Input(self.uuid("date"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("linetype"), "value"),
            ],
        )
        def update_well(well, date, ensembles, linetype):

            ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
            obsplot = [self.observed_plot(well, date)]
            simplots = []
            colors = [
                "#243746",
                "#eb0036",
                "#919ba2",
                "#7d0023",
                "#66737d",
                "#4c9ba1",
                "#a44c65",
                "#80b7bc",
                "#ff1243",
                "#919ba2",
                "#be8091",
                "#b2d4d7",
                "#ff597b",
                "#bdc3c7",
                "#d8b2bd",
                "#ffe7d6",
                "#d5eaf4",
                "#ff88a1",
            ]
            for i, ensemble in enumerate(ensembles):
                if linetype == "realization":
                    simplots.extend(
                        self.simulated_plot(well, date, ensemble, colors[i])
                    )

                if linetype == "fanchart":
                    simplots.extend(
                        self.simulated_stat(well, date, ensemble, colors[i])
                    )

            zon_shapes, zon_names = self.formation_plot(well)
            plot_layout = {
                "yaxis": {"autorange": "reversed", "title": "Depth", "showgrid": False},
                "xaxis": {"title": "Pressure", "showgrid": False},
                "height": 800,
                "margin": {"t": 50},
                "shapes": zon_shapes,
                "updatemenus": [{'type': 'buttons',
                           'buttons': [{'label': 'Play',
                                        'method': 'animate',
                                        'args': [None]}]}]
            }
            return {
                "data": simplots + obsplot + zon_names,
                "layout": plot_layout,
            }

        @app.callback(
            [Output(self.uuid("date"), "options"), Output(self.uuid("date"), "value")],
            [Input(self.uuid("well"), "value"),],
            [State(self.uuid("date"), "value")],
        )
        def update_date(well, current_date):
            dates = self.dates(well)
            available_dates = [{"label": date, "value": date} for date in dates]
            date = current_date if current_date in dates else dates[0]
            return available_dates, date


def add_fanchart_traces(vector_stats, color, legend_group: str):
    """Renders a fanchart for an ensemble vector"""
    # fill_color = color
    # line_color = color
    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    print(vector_stats["maximum"])
    print(vector_stats["maximum"].index)
    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "y": vector_stats["maximum"].index.tolist(),
            "x": vector_stats["maximum"].values,
            "mode": "lines",
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10",
            "y": vector_stats["p10"].index.tolist(),
            "x": vector_stats["p10"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "y": vector_stats["mean"].index.tolist(),
            "x": vector_stats["mean"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "P90",
            "y": vector_stats["p90"].index.tolist(),
            "x": vector_stats["p90"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "y": vector_stats["minimum"].index.tolist(),
            "x": vector_stats["minimum"].values,
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"
