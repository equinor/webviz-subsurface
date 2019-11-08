from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd

import segyio
import xtgeo

from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
from webviz_subsurface_components import LayeredMap
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizContainerABC

from ..datainput.layeredmap._image_processing import array_to_png, get_colormap


class SegyViewer(WebvizContainerABC):
    """### SegyViewer

SegyViewer

* `segyfle`: Input data
"""

    def __init__(
        self,
        app,
        segyfile: Path,
    ):

        self.iline_map_id = "iline-map-id-{}".format(uuid4())
        self.xline_map_id = "xline-map-id-{}".format(uuid4())
        self.depth_map_id = "depth-map-id-{}".format(uuid4())
        self.iline_slider_id = "iline-slider-id-{}".format(uuid4())
        self.xline_slider_id = "xline-slider-id-{}".format(uuid4())
        self.depth_slider_id = "depth-slider-id-{}".format(uuid4())
        self.iline_label_id = "iline-label-id-{}".format(uuid4())
        self.xline_label_id = "xline-label-id-{}".format(uuid4())
        self.depth_label_id = "depth-label-id-{}".format(uuid4())
        self.source = segyio.open(segyfile, "r")
        self.xtgeo_source = xtgeo.Cube(segyfile)
        self.iline_count = len(self.source.ilines)
        self.xline_count = len(self.source.xlines)
        
        self.sample_count = len(self.source.samples)
        self.set_callbacks(app)

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 3fr"),
            children=[
                html.Div(
                    style={"margin": "10px"},
                    children=[
                        html.Label(
                            id=self.depth_label_id,
                            children=f"Depth {self.source.samples[0]}",
                        ),
                        html.Div(
                            style={"margin-bottom": "30px"},
                            children=[
                                dcc.Slider(
                                    id=self.depth_slider_id,
                                    min=1,
                                    max=len(self.source.samples),
                                    value=1,
                                    marks={
                                        i: f"{self.source.samples[i]}"
                                        for i in range(len(self.source.samples))
                                        if i % 50 == 0
                                    },
                                )
                            ],
                        ),
                        LayeredMap(id=self.depth_map_id, layers=[], height=876),
                    ]
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={"margin": "10px"},
                            children=[
                                html.Label(
                                    id=self.iline_label_id,
                                    children=f"Inline {self.source.ilines[0]}",
                                ),
                                html.Div(
                                    style={"margin-bottom": "30px"},
                                    children=[
                                        dcc.Slider(
                                            id=self.iline_slider_id,
                                            min=self.source.ilines[0],
                                            max=self.iline_count,
                                            value=self.source.ilines[0],
                                            marks={
                                                i: i
                                                for i in range(self.iline_count)
                                                if i % 50 == 0
                                            },
                                        )
                                    ],
                                ),
                                LayeredMap(
                                    id=self.iline_map_id, layers=[], height=400,
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px"},
                            children=[
                                html.Label(
                                    id=self.xline_label_id,
                                    children=f"Crossline {self.source.xlines[0]}",
                                ),
                                html.Div(
                                    style={"margin-bottom": "30px"},
                                    children=[
                                        dcc.Slider(
                                            id=self.xline_slider_id,
                                            min=self.source.xlines[0],
                                            max=self.xline_count,
                                            value=self.source.xlines[0],
                                            marks={
                                                i: i
                                                for i in range(self.xline_count)
                                                if i % 50 == 0
                                            },
                                        )
                                    ],
                                ),
                                LayeredMap(
                                    id=self.xline_map_id, layers=[], height=400,
                                ),
                            ],
                        ),
                    ]
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.depth_label_id, "children"),
                Output(self.depth_map_id, "layers"),
            ],
            [Input(self.depth_slider_id, "value")],
        )
        def set_depth(depth):
            print(depth)
            if not depth:
                raise PreventUpdate

            idx = depth
            print('depth index', idx)
            depth_arr = self.source.depth_slice[idx].T.copy()
            bounds = [[0, 0], [self.iline_count, self.xline_count]]
            layer = generate_layer("Depth", depth_arr, bounds=bounds, colormap="RdBu")
            return (f"Depth {self.source.samples[idx]}", [layer])

        @app.callback(
            [
                Output(self.iline_label_id, "children"),
                Output(self.iline_map_id, "layers"),
            ],
            [Input(self.iline_slider_id, "value")],
        )
        def set_iline(iline):
            print(iline)
            if not iline:
                raise PreventUpdate
            iline_arr = self.source.iline[iline].T.copy()
            print(iline, self.xtgeo_source.ilines[iline])
            print('segyio', self.source.iline[iline])
            # print('xtgeo ilines', self.xtgeo_source.ilines)
            idx = np.where(self.xtgeo_source.ilines == iline)
            print('xtgeo', self.xtgeo_source.values[idx,:,:][:,0,:])
            # print(self.xtgeo_source.describe())
            # print(self.xtgeo_source.values[np.where(self.xtgeo_source.ilines[iline]),:,:])


            # print('xtgeo',x)
            bounds = [[0, 0], [self.iline_count-1, self.sample_count-1]]
            layer = generate_layer("inline", iline_arr, bounds=bounds, colormap="RdBu")
            return (f"Inline {self.source.ilines[iline]}", [layer])

        @app.callback(
            [
                Output(self.xline_label_id, "children"),
                Output(self.xline_map_id, "layers"),
            ],
            [Input(self.xline_slider_id, "value")],
        )
        def set_iline(xline):
            print(xline)
            if not xline:
                raise PreventUpdate
            xline_arr = self.source.xline[xline].T.copy()
            bounds = [[0, 0], [self.xline_count-1, self.sample_count-1]]
            layer = generate_layer("inline", xline_arr, bounds=bounds, colormap="RdBu")
            return f"Crossline {self.source.xlines[xline]}", [layer]

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def add_webvizstore(self):
        return [(read_csv, [{"csv_file": self.csv_file}])]


def generate_layer(name, arr, bounds, colormap="RdBu"):
    img = array_to_png(arr)
    return {
        "name": name,
        "checked": True,
        "base_layer": True,
        "hill_shading": False,
        "data": [
            {
                "type": "image",
                "url": img,
                "colormap": get_colormap(colormap),
                "bounds": bounds,
            }
        ],
    }
