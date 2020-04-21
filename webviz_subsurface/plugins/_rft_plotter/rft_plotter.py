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

from plotly.subplots import make_subplots

from ._formation_figure import FormationFigure
from ._map_figure import MapFigure


class RftPlotter(WebvizPluginABC):
    def __init__(
        self,
        app,
        formations: Path,
        simulations: Path,
        observations: Path,
        ertdata: Path = None,
        faultlines: Path = None,
    ):
        super().__init__()
        self.formationdf = pd.read_csv(formations)
        self.simdf = pd.read_csv(simulations)
        self.obsdf = pd.read_csv(observations)

        if ertdata is not None:
            self.ertdatadf = pd.read_csv(ertdata)
            self.ertdatadf["DATE"] = self.ertdatadf["DATE"].apply(
                lambda x: pd.to_datetime(str(x), format="%Y%m%d")
            )
            self.ertdatadf["STDDEV"] = self.ertdatadf.groupby(
                ["WELL", "DATE", "ENSEMBLE"]
            )["SIMULATED"].transform("std")

        self.faultlinesdf = pd.read_csv(faultlines) if faultlines else None
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
    def formation_plot_selectors(self):
        return [
            html.Div(
                [
                    html.Label(style={"font-weight": "bold"}, children="Well",),
                    dcc.Dropdown(
                        id=self.uuid("well"),
                        options=[
                            {"label": well, "value": well} for well in self.well_names
                        ],
                        value=self.well_names[0],
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(style={"font-weight": "bold"}, children="Date",),
                    dcc.RadioItems(
                        id=self.uuid("date"),
                        options=[
                            {"label": date, "value": date}
                            for date in self.dates(self.well_names[0])
                        ],
                        labelStyle={"display": "inline-block", "margin": "5px",},
                        value=self.dates(self.well_names[0])[0],
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(style={"font-weight": "bold"}, children="Ensemble",),
                    dcc.Dropdown(
                        id=self.uuid("ensemble"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.ensembles
                        ],
                        value=self.ensembles[0],
                        multi=True,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Plot simulated results as",
                    ),
                    dcc.RadioItems(
                        id=self.uuid("linetype"),
                        options=[
                            {"label": "Realization lines", "value": "realization",},
                            {
                                "label": "Statistical fanchart (using mean depth)",
                                "value": "fanchart",
                            },
                        ],
                        value="realization",
                    ),
                ]
            ),
        ]

    @property
    def layout(self):

        tabs_styles = {"height": "44px", "width": "50%"}
        tab_style = {
            "borderBottom": "1px solid #d6d6d6",
            "padding": "6px",
            "fontWeight": "bold",
        }

        tab_selected_style = {
            "borderTop": "1px solid #d6d6d6",
            "borderBottom": "1px solid #d6d6d6",
            "backgroundColor": "red",
            "color": "white",
            "padding": "6px",
        }

        return dcc.Tabs(
            style=tabs_styles,
            children=[
                dcc.Tab(
                    label="Rft Map",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            children=[
                                wcc.FlexBox(
                                    children=[
                                        html.Div(
                                            style={"width": "50%"},
                                            children=html.Div(
                                                [
                                                    html.Label(
                                                        style={"font-weight": "bold"},
                                                        children="Ensemble",
                                                    ),
                                                    dcc.Dropdown(
                                                        id=self.uuid("map_ensemble"),
                                                        options=[
                                                            {"label": ens, "value": ens}
                                                            for ens in list(
                                                                self.ertdatadf[
                                                                    "ENSEMBLE"
                                                                ].unique()
                                                            )
                                                        ],
                                                        value=list(
                                                            self.ertdatadf[
                                                                "ENSEMBLE"
                                                            ].unique()
                                                        )[0],
                                                    ),
                                                    html.Label(
                                                        style={"font-weight": "bold"},
                                                        children="Size by",
                                                    ),
                                                    dcc.Dropdown(
                                                        id=self.uuid("map_size"),
                                                        options=[
                                                            {
                                                                "label": "Standard Deviation",
                                                                "value": "STDDEV",
                                                            },
                                                            {
                                                                "label": "Misfit",
                                                                "value": "DIFF",
                                                            },
                                                        ],
                                                        value="DIFF",
                                                    ),
                                                    html.Label(
                                                        style={"font-weight": "bold"},
                                                        children="Color by",
                                                    ),
                                                    dcc.Dropdown(
                                                        id=self.uuid("map_color"),
                                                        options=[
                                                            {
                                                                "label": "Misfit",
                                                                "value": "DIFF",
                                                            },
                                                            {
                                                                "label": "Standard Deviation",
                                                                "value": "STDDEV",
                                                            },
                                                            {
                                                                "label": "Year",
                                                                "value": "YEAR",
                                                            },
                                                            
                                                        ],
                                                        value="STDDEV",
                                                    ),
                                                    html.Label(
                                                        style={"font-weight": "bold"},
                                                        children="Date range",
                                                    ),
                                                    html.Div(
                                                        style={"width": "50%"},
                                                        children=[
                                                            dcc.RangeSlider(
                                                                id=self.uuid(
                                                                    "map_date"
                                                                ),
                                                                min=self.ertdatadf[
                                                                    "YEAR"
                                                                ].min(),
                                                                max=self.ertdatadf[
                                                                    "YEAR"
                                                                ].max(),
                                                                value=[
                                                                    self.ertdatadf[
                                                                        "YEAR"
                                                                    ].min(),
                                                                    self.ertdatadf[
                                                                        "YEAR"
                                                                    ].max(),
                                                                ],
                                                                tooltip={
                                                                    "always_visible": True
                                                                },
                                                            )
                                                        ],
                                                    ),
                                                ]
                                            ),
                                        ),
                                        html.Div(
                                            style={"width": "50%"},
                                            children=self.formation_plot_selectors,
                                        ),
                                    ]
                                ),
                                wcc.FlexBox(
                                    children=[
                                        wcc.Graph(
                                            style={"width": "50%"}, id=self.uuid("map"),
                                        ),
                                        wcc.Graph(
                                            style={"width": "50%"},
                                            id=self.uuid("graph"),
                                            figure={
                                                "layout": {
                                                    "height": 800,
                                                    "margin": {"t": 50},
                                                    "xaxis": {"showgrid": False},
                                                    "yaxis": {"showgrid": False},
                                                }
                                            },
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                ),
                dcc.Tab(
                    label="Rft misfit per real",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        wcc.FlexBox(
                            [
                                dcc.Dropdown(
                                    style={"width": "80%"},
                                    id=self.uuid("well-misfit"),
                                    options=[
                                        {"label": well, "value": well}
                                        for well in self.well_names
                                    ],
                                    value=self.well_names,
                                    multi=True,
                                ),
                                html.Button(
                                    id=self.uuid("well-misfit-all"),
                                    children=["Select all"],
                                ),
                            ]
                        ),
                        dcc.Dropdown(
                            id=self.uuid("ensemble-misfit"),
                            options=[
                                {"label": ens, "value": ens}
                                for ens in list(self.ertdatadf["ENSEMBLE"].unique())
                            ],
                            value=list(self.ertdatadf["ENSEMBLE"].unique())[0],
                        ),
                        wcc.Graph(id=self.uuid("misfit-graph")),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("well"), "value"), [Input(self.uuid("map"), "clickData"),],
        )
        def get_clicked_well(clickData):
            if not clickData:
                return self.well_names[0]
            for layer in clickData["points"]:
                try:
                    return layer["customdata"]
                except KeyError:
                    pass
            raise PreventUpdate

        @app.callback(
            Output(self.uuid("map"), "figure"),
            [
                Input(self.uuid("map_ensemble"), "value"),
                Input(self.uuid("map_size"), "value"),
                Input(self.uuid("map_color"), "value"),
                Input(self.uuid("map_date"), "value"),
            ],
        )
        def update_map(ensemble, sizeby, colorby, dates):
            figure = MapFigure(self.ertdatadf, ensemble)
            figure.add_misfit_plot(sizeby, colorby, dates)
            if self.faultlinesdf is not None:
                figure.add_fault_lines(self.faultlinesdf)
            return {"data": figure.traces, "layout": figure.layout}

        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("well"), "value"),
                Input(self.uuid("date"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("linetype"), "value"),
            ],
        )
        def update_formation_plot(well, date, ensembles, linetype):
            if date not in self.dates(well):
                raise PreventUpdate

            figure = FormationFigure(
                well, self.formationdf, self.simdf, self.obsdf, self.ertdatadf
            )

            figure.add_formation()
            if linetype == "realization":
                figure.add_simulated_lines(date, ensembles)
            if linetype == "fanchart":
                figure.add_fanchart(date, ensembles)

            figure.add_observed(date)
            figure.add_ert_observed(date)

            return {
                "data": figure.traces,
                "layout": figure.layout,
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

        @app.callback(
            Output(self.uuid("well-misfit"), "value"),
            [Input(self.uuid("well-misfit-all"), "n_clicks"),],
        )
        def select_all(n_clicks):
            return self.well_names

        @app.callback(
            Output(self.uuid("misfit-graph"), "figure"),
            [Input(self.uuid("well-misfit"), "value"),],
        )
        def update_misfit(wells):
            wells = wells if isinstance(wells, list) else [wells]

            df = self.ertdatadf[self.ertdatadf["WELL"].isin(wells)]
            fig = make_subplots(
                rows=len(list(df["ENSEMBLE"].unique())), cols=1, vertical_spacing=0.05,
            )
            max_diff = 0
            mean_diff_ens = []
            for i, (ens, ensdf) in enumerate(df.groupby("ENSEMBLE")):

                realdf = ensdf.groupby("REAL").sum().reset_index()
                max_diff = (
                    max_diff
                    if max_diff > realdf["DIFF"].max()
                    else realdf["DIFF"].max()
                )
                mean_diff_ens.append(realdf["DIFF"].mean())
                realdf = realdf.sort_values(by=["DIFF"])
                trace = {
                    "x": realdf["REAL"],
                    "y": realdf["DIFF"],
                    "type": "bar",
                }

                fig.add_trace(trace, i + 1, 1)

            # Add mean line

            layout = fig["layout"]
            layout.update({"height": 800})
            shapes = []

            for i, mean_diff in enumerate(mean_diff_ens):
                if i == 0:
                    layout.update(
                        {
                            "xaxis": {"type": "category"},
                            "yaxis": {"range": [0, max_diff]},
                        }
                    )
                    for j, mean_diff2 in enumerate(mean_diff_ens):
                        if j == 0:
                            shapes.append(
                                dict(
                                    type="line",
                                    yref="y",
                                    y0=mean_diff,
                                    y1=mean_diff,
                                    xref="paper",
                                    x0=0,
                                    x1=1,
                                )
                            )
                        else:
                            shapes.append(
                                dict(
                                    type="line",
                                    yref=f"y{j+1}",
                                    y0=mean_diff,
                                    y1=mean_diff,
                                    xref="paper",
                                    x0=0,
                                    x1=1,
                                )
                            )
                else:
                    layout.update(
                        {
                            f"xaxis{i+1}": {"type": "category"},
                            f"yaxis{i+1}": {"range": [0, max_diff]},
                        }
                    )
                    for j, mean_diff2 in enumerate(mean_diff_ens):
                        if j == 0:
                            shapes.append(
                                dict(
                                    type="line",
                                    yref="y",
                                    y0=mean_diff,
                                    y1=mean_diff,
                                    xref="paper",
                                    x0=0,
                                    x1=1,
                                )
                            )
                        else:
                            shapes.append(
                                dict(
                                    type="line",
                                    yref=f"y{j+1}",
                                    y0=mean_diff,
                                    y1=mean_diff,
                                    xref="paper",
                                    x0=0,
                                    x1=1,
                                )
                            )
            layout["shapes"] = shapes
            data = fig["data"]
            return {"data": data, "layout": layout}
