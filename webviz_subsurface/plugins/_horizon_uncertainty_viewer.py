from uuid import uuid4
from pathlib import Path
from typing import List
import dash
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from matplotlib.colors import ListedColormap
import xtgeo
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.utils import calculate_slider_step

from .._datainput.seismic import load_cube_data
from .._datainput.well import load_well
from .._datainput.surface import make_surface_layer, get_surface_fence


class HorizonUncertaintyViewer(WebvizPluginABC):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    """### SurfaceWithSeismicCrossSection

This plugin visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.


* `segyfiles`: List of file paths to SEG-Y files
* `segynames`: Corresponding list of displayed seismic names
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    def __init__(
        self,
        app,
        surfacefiles: List[Path],
        wellfiles: List[Path],
        surfacenames: list = None,
        wellnames: list = None,
        zunit="depth (m)",
    ):

        super().__init__()
        self.zunit = zunit
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]
        
        self.wellfiles = [str(wellfile) for wellfile in wellfiles]
        if wellnames is not None:
            if len(wellnames) != len(wellfiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.wellnames = wellnames
        else:
            self.wellnames = [Path(wellfile).stem for wellfile in wellfiles]
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "Plugin to display surfaces and random lines from a seismic cube. "
                ),
            },
            {"id": self.ids("surface"), "content": ("The visualized surface."),},
            {"id": self.ids("well"), "content": ("The visualized well."),},
            {
                "id": self.ids("map-view"),
                "content": (
                    "Map view of the surface. Use the right toolbar to "
                    "draw a random line."
                ),
            },
        ]

    @property
    def surface_layout(self):
        """Layout for surface section"""
        return html.Div(
            children=[
                wcc.FlexBox(
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select surface",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("surface"),
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.surfacenames, self.surfacefiles
                                        )
                                    ],
                                    value=self.surfacefiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select well",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("well"),
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.wellnames, self.wellfiles
                                        )
                                    ],
                                    value=self.wellfiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={
                                "marginTop": "20px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=wcc.Graph(
                                figure={"displayModeBar": True}, id=self.ids("map-view")
                            ),
                        )
                    ]
                ),
            ]
        )


    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                html.Div(style={"flex": 1}, children=self.surface_layout),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "figure"),
            [
                Input(self.ids("surface"), "value"),
                Input(self.ids("well"), "value"),
            ],
        )
        def _render_surface(
            surfacepath, wellpath
        ):
            print(surfacepath)
            print(wellpath)
            well = xtgeo.Well(get_path(wellpath))
            surface = xtgeo.RegularSurface(get_path(surfacepath),fformat='irap_binary')
            return make_figure(well,surface)

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.segyfiles + self.surfacefiles]



@webvizstore
def get_path(path) -> Path:
    return Path(path)

def make_figure(
    well,
    surface,
):
    #Generate a polyline along a well path
    well_fence = well.get_fence_polyline(nextend=0, sampling=5)
    #Get surface values along the polyline
    surf_line = surface.get_randomline(well_fence)
    well.create_relative_hlen()
    df = well.dataframe
    layout = {}
    layout.update(
        {
            "yaxis": {
                "autorange": "reversed",
            },
        }
    )
    return {
        'data': [
                {
                "type": "line",
                "y": surf_line[:,1],
                "x": surf_line[:,0],
                "name": "surface",
                },
                {
                "type": "line",
                "y": df["Z_TVDSS"],
                "x": df["R_HLEN"],
                "name": "well"
                },
        ],
        "layout": layout,
    }
