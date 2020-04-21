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

from webviz_subsurface._datainput.fmu_input import load_csv
from ._formation_figure import FormationFigure
from ._map_figure import MapFigure
from ._misfit_figure import update_misfit_plot


class RftPlotter(WebvizPluginABC):
    def __init__(
        self,
        app,
        ensembles,
        formations: Path,
        observations: Path,
        ertdata: Path = None,
        faultlines: Path = None,
    ):
        super().__init__()
        self.formationdf = pd.read_csv(formations)
        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.simdf = load_csv(self.ens_paths, "share/results/tables/rft.csv")
        # self.simdf = pd.read_csv(simulations)
        self.obsdf = pd.read_csv(observations)

        if ertdata is not None:
            self.ertdatadf = pd.read_csv(ertdata)
            #           self.ertdatadf["DATE"] = self.ertdatadf["DATE"].apply(
            #               lambda x: pd.to_datetime(str(x), format="%Y%m%d")
            #           )
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
    def map_plot_selectors(self):
        return (
            html.Div(
                [
                    html.Label(style={"font-weight": "bold"}, children="Ensemble",),
                    dcc.Dropdown(
                        id=self.uuid("map_ensemble"),
                        options=[
                            {"label": ens, "value": ens}
                            for ens in list(self.ertdatadf["ENSEMBLE"].unique())
                        ],
                        value=list(self.ertdatadf["ENSEMBLE"].unique())[0],
                    ),
                    html.Label(style={"font-weight": "bold"}, children="Size by",),
                    dcc.Dropdown(
                        id=self.uuid("map_size"),
                        options=[
                            {"label": "Standard Deviation", "value": "STDDEV",},
                            {"label": "Misfit", "value": "DIFF",},
                        ],
                        value="DIFF",
                    ),
                    html.Label(style={"font-weight": "bold"}, children="Color by",),
                    dcc.Dropdown(
                        id=self.uuid("map_color"),
                        options=[
                            {"label": "Misfit", "value": "DIFF",},
                            {"label": "Standard Deviation", "value": "STDDEV",},
                            {"label": "Year", "value": "YEAR",},
                        ],
                        value="STDDEV",
                    ),
                    html.Label(style={"font-weight": "bold"}, children="Date range",),
                    html.Div(
                        style={"width": "100%"},
                        children=[
                            dcc.RangeSlider(
                                id=self.uuid("map_date"),
                                min=self.ertdatadf["DATE"].min(),
                                max=self.ertdatadf["DATE"].max(),
                                value=[
                                    self.ertdatadf["DATE"].min(),
                                    self.ertdatadf["DATE"].max(),
                                ],
                                tooltip={"always_visible": True},
                            )
                        ],
                    ),
                ]
            ),
        )

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
                                            children=self.map_plot_selectors,
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
            if self.faultlinesdf is not None:
                figure.add_fault_lines(self.faultlinesdf)
            figure.add_misfit_plot(sizeby, colorby, dates)

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
        def misfit_plot(wells):

            return update_misfit_plot(self.ertdatadf, wells)
