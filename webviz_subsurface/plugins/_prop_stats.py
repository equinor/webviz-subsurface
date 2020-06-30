from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.fmu_input import load_csv, load_parameters, load_ensemble_set
from .._private_plugins.parameter_filter import ParameterFilter


class PropertyStatistics(WebvizPluginABC):
    """### PropertyStatistics

"""

    SELECTORS = ["ENSEMBLE", "SOURCE", "PROPERTY", "ZONE", "FACIES", "LICENSE"]

    def __init__(
        self,
        app,
        regionfile: Path,
        ensembles: list = None,
        propstatfile: Path = "share/results/tables/propstats.csv",
    ):

        super().__init__()

        if ensembles is not None:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.propdf = load_ensemble_set(self.ens_paths, filter_file=None).load_csv(
                propstatfile
            )
            self.parameterdf = load_parameters(
                filter_file=None,
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
            )
            self.propdf.to_parquet("/tmp/tmp/props.parquet", index=False)
            self.parameterdf.to_parquet("/tmp/tmp/parameters.parquet", index=False)
        else:
            self.propdf = pd.read_parquet("/tmp/tmp/props.parquet")
            self.parameterdf = pd.read_parquet("/tmp/tmp/parameters.parquet")
        self.geojson = read_json(regionfile)
        self.center = find_geocenter(self.geojson)
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.pfilter = ParameterFilter(app, self.parameterdf.copy())
        self.set_callbacks(app)

    @property
    def selectors(self):
        """List of available selector columns in dframe"""
        return [x for x in PropertyStatistics.SELECTORS if x in self.propdf.columns]

    @property
    def selector_layout(self):
        return wcc.FlexBox(
            children=[
                html.Div(
                    children=[
                        html.Div(
                            children=[
                                html.Label(selector),
                                dcc.Dropdown(
                                    id={
                                        "index": selector,
                                        "page": self.uuid("selectors"),
                                    },
                                    options=[
                                        {"label": sel_val, "value": sel_val}
                                        for sel_val in self.propdf[selector].unique()
                                    ],
                                    value=self.propdf[selector].unique()[0],
                                    clearable=False,
                                ),
                            ]
                        )
                        for selector in self.selectors
                    ]
                ),
                self.pfilter.layout,
            ]
        )

    @property
    def layout(self):
        tabs_styles = {"height": "44px", "width": "100%"}
        tab_style = {
            "borderBottom": "1px solid #d6d6d6",
            "padding": "6px",
            "fontWeight": "bold",
        }

        tab_selected_style = {
            "borderTop": "1px solid #d6d6d6",
            "borderBottom": "1px solid #d6d6d6",
            "backgroundColor": "#007079",
            "color": "white",
            "padding": "6px",
        }
        return html.Div(
            [
                html.H1("Grid property statistics per region"),
                wcc.FlexBox(
                    children=[
                        html.Div(style={"flex": 1}, children=self.selector_layout),
                        html.Div(
                            style={"flex": 4},
                            children=dcc.Tabs(
                                style=tabs_styles,
                                children=[
                                    dcc.Tab(
                                        label="Histogram per region",
                                        style=tab_style,
                                        selected_style=tab_selected_style,
                                        children=wcc.FlexBox(
                                            children=[
                                                html.Div(
                                                    style={"flex": 3},
                                                    children=wcc.Graph(
                                                        id=self.uuid("region-graph")
                                                    ),
                                                ),
                                                html.Div(
                                                    style={"flex": 3},
                                                    children=[
                                                        dcc.RadioItems(
                                                            id=self.uuid(
                                                                "graph-select"
                                                            ),
                                                            options=[
                                                                {
                                                                    "label": "Histogram",
                                                                    "value": "Histogram",
                                                                },
                                                                {
                                                                    "label": "Barchart",
                                                                    "value": "Barchart",
                                                                },
                                                                {
                                                                    "label": "Scatter",
                                                                    "value": "Scatter",
                                                                },
                                                                {
                                                                    "label": "Correlations",
                                                                    "value": "Correlations",
                                                                },
                                                            ],
                                                            value="Scatter",
                                                        ),
                                                        wcc.Graph(
                                                            id=self.uuid("hist-graph")
                                                        ),
                                                    ],
                                                ),
                                            ]
                                        ),
                                    ),
                                    dcc.Tab(
                                        label="Ranked on input parameters",
                                        style=tab_style,
                                        selected_style=tab_selected_style,
                                        children=wcc.FlexBox(
                                            children=[
                                                html.Div(
                                                    style={"flex": 3},
                                                    children=wcc.Graph(
                                                        id=self.uuid("region-graph2"),
                                                        config={
                                                            "modeBarButtonsToRemove": [
                                                                "select2d",
                                                                "lasso2d",
                                                            ]
                                                        },
                                                    ),
                                                ),
                                                html.Div(
                                                    style={"flex": 3},
                                                    children=wcc.Graph(
                                                        id=self.uuid("corr-graph"),
                                                    ),
                                                ),
                                            ]
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ]
                ),
            ]
        )

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def cloropleth(self, df):
        return px.choropleth_mapbox(
            df,
            geojson=self.geojson,
            locations="REGION",
            color="Avg",
            color_continuous_scale="Viridis",
            range_color=(0, df["Avg"].max()),
            mapbox_style="carto-positron",
            zoom=10,
            center=self.center,
            opacity=0.5,
            labels={"Avg": "Average"},
            height=800,
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("region-graph"), "figure"),
            [
                Input({"page": self.uuid("selectors"), "index": ALL}, "value"),
                Input(self.pfilter.storage_id, "data"),
            ],
            [State({"page": self.uuid("selectors"), "index": "ENSEMBLE"}, "value"),],
        )
        def _update_region_graph(selectors, p_filter, ensemble):
            inputs = dash.callback_context.inputs_list[0]
            df = self.propdf.copy()
            for sel_input in inputs:
                df = df[df[sel_input["id"]["index"]] == sel_input["value"]]
            df = filter_reals(df, ensemble, p_filter)
            df = df.groupby(self.selectors + ["REGION"],).mean().reset_index()
            fig = self.cloropleth(df)
            fig.update_layout(dragmode="lasso", uirevision="keep")
            fig["layout"].update(self.plotly_theme["layout"])
            return fig

        @app.callback(
            Output(self.uuid("hist-graph"), "figure"),
            [
                Input(self.uuid("region-graph"), "selectedData"),
                Input({"page": self.uuid("selectors"), "index": ALL}, "value"),
                Input(self.pfilter.storage_id, "data"),
                Input(self.uuid("graph-select"), "value"),
            ],
            [State({"page": self.uuid("selectors"), "index": "ENSEMBLE"}, "value"),],
        )
        def _update_hist_graph(cd, selectors, p_filter, graph_type, ensemble):
            if cd is None:
                regions = list(self.propdf["REGION"].unique())

            else:
                regions = [point["location"] for point in cd["points"]]
            if len(regions) == 0:
                return {"data": []}
            inputs = dash.callback_context.inputs_list[1]
            df = self.propdf.copy()
            parameterdf = self.parameterdf.copy()
            df = df[df["REGION"].isin(regions)]
            for sel_input in inputs:
                df = df[df[sel_input["id"]["index"]] == sel_input["value"]]
            df = filter_reals(df, ensemble, p_filter)
            df2 = df.copy()
            if graph_type == "Histogram":
                fig = px.histogram(
                    df2, x="Avg", facet_col="REGION", facet_col_wrap=3, height=800
                )
            elif graph_type == "Barchart":
                fig = px.bar(
                    df2,
                    x="REAL",
                    y="Avg",
                    facet_col="REGION",
                    facet_col_wrap=3,
                    height=800,
                )
            elif graph_type == "Scatter":
                fig = px.scatter(
                    df2,
                    x="REAL",
                    y="Avg",
                    facet_col="REGION",
                    facet_col_wrap=3,
                    height=800,
                )
            else:
                response = "Avg"
                parameterdf = parameterdf.loc[
                        parameterdf["ENSEMBLE"] == ensemble
                    ]
                dframe = pd.merge(df, parameterdf, on=["REAL"])
                corrdf = correlate(dframe, response=response)
                try:
                    corr_response = (
                        corrdf[response].dropna().drop(["REAL", response], axis=0)
                    )

                    fig = make_correlation_plot(
                        corr_response, response, self.plotly_theme["layout"]
                    )
                except KeyError:
                    return {
                        "layout": {
                            "title": "<b>Cannot calculate correlation for given selection</b><br>"
                            "Select a different response or filter setting."
                        }
                    }
            fig["layout"].update(self.plotly_theme["layout"])
            print(fig)
            return fig

        @app.callback(
            Output(self.uuid("region-graph2"), "figure"),
            [Input({"page": self.uuid("selectors"), "index": ALL}, "value")],
        )
        def _update_region_graph2(*args):
            inputs = dash.callback_context.inputs_list[0]
            df = self.propdf.copy()
            for sel_input in inputs:
                df = df[df[sel_input["id"]["index"]] == sel_input["value"]]
            df = df.groupby(self.selectors + ["REGION"],).mean().reset_index()
            fig = self.cloropleth(df)
            fig.update_layout(uirevision="keep")
            fig["layout"].update(self.plotly_theme["layout"])
            return fig


def read_json(jsonfile: Path):
    with jsonfile.open() as jsfile:
        return json.loads(jsfile.read())


def find_geocenter(geojson_file):
    lat = []
    lon = []
    for feature in geojson_file["features"]:
        for coords in feature["geometry"]["coordinates"]:
            for coord in coords:
                lat.append(coord[1])
                lon.append(coord[0])
    return {
        "lat": (np.max(lat) + np.min(lat)) / 2,
        "lon": (np.max(lon) + np.min(lon)) / 2,
    }


def filter_reals(df, ensemble, p_filter):
    if p_filter is not None:
        p_filter = json.loads(p_filter)
        if p_filter.get(ensemble):
            df = df[df["REAL"].isin(p_filter.get(ensemble))]
    return df


def correlate(inputdf, response, method="pearson"):
    df = inputdf.copy()
    """Returns the correlation matrix for a dataframe"""
    if method == "pearson":
        corrdf = df.corr(method=method)
    elif method == "spearman":
        corrdf = df.rank().corr(method="pearson")
    else:
        raise ValueError(
            f"Correlation method {method} is invalid. "
            "Available methods are 'pearson' and 'spearman'"
        )
    return corrdf.reindex(corrdf[response].abs().sort_values().index)


def make_correlation_plot(series, response, theme, corr_method="pearson"):
    """Make Plotly trace for correlation plot"""
    layout = theme
    layout.update(
        {
            "barmode": "relative",
            "margin": {"l": 200, "r": 50, "b": 20, "t": 100},
            "height": 750,
            # "xaxis": {"range": [-1, 1]},
            "title": f"Correlations ({corr_method}) between {response} and input parameters",
        },
    )
    layout["font"].update({"size": 8})

    return {
        "data": [
            {"x": series.values, "y": series.index, "orientation": "h", "type": "bar"}
        ],
        "layout": layout,
    }
