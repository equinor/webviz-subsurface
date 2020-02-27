import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate

import pandas as pd
from webviz_config import WebvizPluginABC


class PolygonMap(WebvizPluginABC):

    """A webviz container for displaying isochore thickness per region, across ensemble,
       based on (custom) output from RMS"""

    def __init__(
        self,
        app,
        title: str,
        faultlines_file: str = None,
        wellpicks_file: str = None,
        regions_file: str = None,
        thickness_file: str = None,
    ):

        self.title = title

        self.wellpicks_data = (
            self.load_wellpicks_data(
                fname=wellpicks_file, horizon_name="VIKING_GP_Top",
            )
            if wellpicks_file
            else None
        )
        self.faultlines_data = (
            self.load_faultlines_data(faultlines_file) if faultlines_file else None
        )
        self.thickness_data = (
            self.load_thickness_data(thickness_file) if thickness_file else None
        )
        self.regions_data = (
            self.load_regions_data(regions_file) if regions_file else None
        )
        self.active_region = "TON_N"
        self.curvenumbers = {}

        (
            (self.map_xmax, self.map_xmin),
            (self.map_ymax, self.map_ymin),
        ) = self.find_map_min_max(self.regions_data)

        # self.reals = self.thickness_data["REAL"].unique()
        self.reals = [0, 1, 2]
        self.nreals = len(self.reals)

        self.set_styles()

        self.set_callbacks(app)

    def set_styles(self):
        self.histogram_style = {
            #'width' : '20vw',
            #'height' : '10vw',
        }

        map_width_vh = 30
        map_ratio = (self.map_ymax - self.map_ymin) / (self.map_xmax - self.map_xmin)
        map_height_vh = map_width_vh / map_ratio

        self.container_style = {
            "display": "flex",
        }

        self.histograms_container_style = {
            "display": "flex",
            "flex-flow": "wrap",
        }

        self.map_container_style = {
            "min-width": "30vw",
            "margin": 0,
        }

        self.map_style = {
            #'height' : '{}vw'.format(round(map_height_vh, 0)),
            #'width' : '{}vw'.format(round(map_width_vh, 0)),
        }

    #### DATA LOADERS

    def load_wellpicks_data(self, fname, horizon_name):

        df = pd.read_csv(fname)
        df = df[(df["REAL"] == 0) & (df["Horizon"] == horizon_name)]
        df = df[["REAL", "Horizon", "X", "Y"]].reset_index(drop=True)

        if len(df) == 0:
            raise ValueError(
                "Filtering down wellpicks to horizon"
                + "{} and realization 0 resulted in zero entries.".format(
                    horizon_name, 0
                )
            )

        return df

    def load_faultlines_data(self, fname):

        df = pd.read_csv(fname)

        # check if csv was exported with an index. If so, drop it.
        if "Unnamed: 0" in df.columns:
            del df["Unnamed: 0"]

        if len(df["REAL"]) > 1:
            df = df[df["REAL"] == 0]

        return df

    def load_thickness_data(self, fname):

        df = pd.read_csv(fname)

        # check if csv was exported with an index. If so, drop it.
        if "Unnamed: 0" in df.columns:
            del df["Unnamed: 0"]

        return df

    def load_regions_data(self, fname):

        df = pd.read_csv(fname, na_values=[-999, -999.25, 999])

        return df

    #### DATA HANDLERS

    def find_map_min_max(self, df):

        """Given a dataframe, return the max/min range of x and y columns"""

        return (
            (df["X_UTME"].max(), df["X_UTME"].min()),
            (df["Y_UTMN"].max(), df["Y_UTMN"].min()),
        )

    def get_intervals(self):
        """From the thickness data, get the stratigraphic intervals included"""
        intervals = [
            c for c in self.thickness_data.columns if c not in ["REAL", "Region"]
        ]
        return intervals

    ##### LAYOUT
    @property
    def layout(self):

        # intervals = self.get_intervals()

        return html.Div(
            [
                html.H1(self.active_region, id="active_region_header"),
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=self.make_map(),
                                    id="map_base",
                                    style=self.map_style,
                                    config={"displayModeBar": False},
                                ),
                            ],
                            style=self.map_container_style,
                        ),
                        html.Div(
                            [
                                dcc.Graph(id = 'histogram')
                            ],
                            
                        ),
                    ],
                    id="container",
                    style=self.container_style,
                ),

            ]
        )

    ##### CALLBACKS
    def set_callbacks(self, app):
        @app.callback(
            [
                Output("map_base", "figure"),
                Output("histogram", "figure"),
                Output("active_region_header", "children"),
            ],
            [Input("map_base", "clickData")],
            [State("map_base", "figure")],
        )
        def _update_graph(clickData, figure):
            if clickData is None:
                raise PreventUpdate
            points = clickData.get("points", [None])[0]
            if points is not None:
                curvenumber = points.get("curveNumber", None)
            region = self.curvenumbers.get(curvenumber, None)
            self.active_region = region

            for trace in figure["data"]:
                if trace.get("text"):
                    if trace["text"] == self.active_region:
                        trace["fillcolor"] = "red"
                    else:
                        trace["fillcolor"] = None
            return figure, self.make_histogram(region), self.active_region

    def make_histogram(self, region):
        """Create and return histogram"""

        df = self.thickness_data
        layout = {
            "margin": go.layout.Margin(l=100, r=1, b=20, t=100, pad=1),
            "height": 300,
            "width": 300,
            "yaxis": {
                "zeroline": False,
                "showline": False,
                "showticklabels": False,
                "showgrid": False,
                # "title": {"text": interval},
            },
            "xaxis": {"title": {"text": "Contact distribution (m)"},},
            "bargap": 0.1,
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        }       

        style = self.histogram_style

        no_data = False
        marker_color = "grey"
        try:
          values = df[region]
        except KeyError:
          layout.get("yaxis").update({"range": [0, 1]})
          layout.get("xaxis").update({
                "zeroline": False,
                "showline": False,
                "showticklabels": False,
                "showgrid": False,
                "title": "",
            })
          return {'data':[], "layout":layout}

        data = [
            go.Histogram(
                x=values,
                name=region,
                marker_color=marker_color,
                showlegend=False,
            )
        ]



        if no_data:
            layout.get("yaxis").update({"range": [0, 1]})

        figure = go.Figure(data=data, layout=layout)

        if no_data:
            figure.add_trace(
                go.Scatter(
                    x=[0],
                    y=[0.5],
                    mode="text",
                    text=["All realizations = 0.0"],
                    textposition="bottom center",
                    showlegend=False,
                )
            )
        return figure
        

    ##### WEB ELEMENTS
    def make_map(self):
        """Create and return the map figure"""

        # build plots by adding traces to traces
        traces = []

        # Track curvenumbers.
        # The clickevents returns "curvenumber", which seems to be
        # an incrementally increasing index of the traces within
        # a figure. So to be able to translate curve numbers back to
        # content, I'm adding my own curvenumber that follows the
        # traces.

        curvenumbers = {}
        curvenumber = 0

        # df_faults = self.faultlines_data
        # df_picks = self.wellpicks_data

        # # add faultlines
        # valid_faults = []
        # for f in df_faults["id"].unique():
        #     if len(df_faults[df_faults["id"] == f]) > 3:
        #         valid_faults.append(f)

        # for f in valid_faults:
        #     trace = go.Scatter(
        #         x=df_faults[df_faults["id"] == f]["x"],
        #         y=df_faults[df_faults["id"] == f]["y"],
        #         mode="lines",
        #         line={"color": "grey", "width": 1, "simplify": True,},
        #         showlegend=False,
        #         hoverinfo="none",
        #     )
        #     curvenumbers[curvenumber] = "a fault"
        #     curvenumber += 1
        #     traces.append(trace)

        # # add wellpicks
        # trace = go.Scatter(
        #     x=df_picks["X"],
        #     y=df_picks["Y"],
        #     mode="markers",
        #     line={"color": "black"},
        #     showlegend=False,
        #     hoverinfo="none",
        # )
        # traces.append(trace)
        # curvenumbers[curvenumber] = "a well"
        # curvenumber += 1

        # regions
        for region in self.regions_data["NAME"].unique():
            df_this_region = self.regions_data[self.regions_data["NAME"] == region]

            if region == self.active_region:
                linecolor = "rgba(100,10,10,0.5)"
                linewidth = 2
                fillcolor = "red"
            else:
                linecolor = "grey"
                linewidth = 1
                fillcolor = "rgba(0,0,0,0.1)"

            xs = df_this_region["X_UTME"]
            ys = df_this_region["Y_UTMN"]

            trace = go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": linecolor, "width": linewidth},
                hoveron="fills",
                hoverinfo="text",
                hovertext=region,
                text=region,
                showlegend=False,
                fill="toself",
                fillcolor=fillcolor,
            )

            traces.append(trace)
            curvenumbers[curvenumber] = region
            curvenumber += 1

        self.curvenumbers = curvenumbers

        layout = {
            #'autosize' : True,
            "width": 600,
            "yaxis": {
                "zeroline": False,
                "showline": False,
                "showticklabels": True,
                "showgrid": False,
                #'scaleanchor' : 'x',
            },
            "xaxis": {
                "zeroline": False,
                "showline": False,
                "showticklabels": True,
                "showgrid": False,
                "range": [self.map_xmin, self.map_xmax],
                "scaleanchor": "y",
            },
            "hovermode": "closest",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": go.layout.Margin(l=1, r=1, b=1, t=100, pad=1),
        }

        figure = go.Figure(data=traces, layout=layout)

        w = figure.layout.width

        r = (self.map_ymax - self.map_ymin) / (self.map_xmax - self.map_xmin)
        h = w * r

        figure.layout.update({"height": h})

        return figure
