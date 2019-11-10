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

    def __init__(self, app, segyfile: Path):

        self.iline_map_id = "iline-map-id-{}".format(uuid4())
        self.xline_map_id = "xline-map-id-{}".format(uuid4())
        self.depth_map_id = "depth-map-id-{}".format(uuid4())
        self.iline_slider_id = "iline-slider-id-{}".format(uuid4())
        self.xline_slider_id = "xline-slider-id-{}".format(uuid4())
        self.depth_slider_id = "depth-slider-id-{}".format(uuid4())
        self.iline_label_id = "iline-label-id-{}".format(uuid4())
        self.xline_label_id = "xline-label-id-{}".format(uuid4())
        self.depth_label_id = "depth-label-id-{}".format(uuid4())
        # self.source = segyio.open(segyfile, "r")
        self.xtgeo_source = xtgeo.Cube(segyfile)
        self.iline_count = len(self.xtgeo_source.ilines)
        self.xline_count = len(self.xtgeo_source.xlines)

        self.sample_count = len(self.xtgeo_source.zslices)
        self.set_callbacks(app)

    @property
    def slice_layout(self):
        return html.Div(
            style={"margin": "10px"},
            children=[
                html.Label(
                    id=self.depth_label_id,
                    children=f"Depth {self.xtgeo_source.zslices[0]}",
                ),
                html.Div(
                    style={"margin-bottom": "30px"},
                    children=[
                        dcc.Slider(
                            id=self.depth_slider_id,
                            min=self.xtgeo_source.zslices[0],
                            max=self.xtgeo_source.zslices[-1],
                            value=self.xtgeo_source.zslices[0],
                            updatemode='drag',
                            step = self.xtgeo_source.zinc,
                            marks={
                                str(i): str(i)
                                for i in self.xtgeo_source.zslices
                                if i % 50 == 0
                            },
                        )
                    ],
                ),
                LayeredMap(id=self.depth_map_id, layers=[], height=876),
            ],
        )

    @property
    def iline_layout(self):
        return html.Div(
            style={"margin": "10px"},
            children=[
                html.Label(
                    id=self.iline_label_id,
                    children=f"Inline {self.xtgeo_source.ilines[0]}",
                ),
                html.Div(
                    style={"margin-bottom": "30px"},
                    children=[
                        dcc.Slider(
                            id=self.iline_slider_id,
                            min=self.xtgeo_source.ilines[0],
                            max=self.iline_count - 1,
                            value=self.xtgeo_source.ilines[0],
                            updatemode='drag',
                            marks={
                                i: i for i in range(self.iline_count) if i % 50 == 0
                            },
                        )
                    ],
                ),
                LayeredMap(id=self.iline_map_id, layers=[], height=400),
            ],
        )

    @property
    def xline_layout(self):
        return html.Div(
            style={"margin": "10px"},
            children=[
                html.Label(
                    id=self.xline_label_id,
                    children=f"Crossline {self.xtgeo_source.xlines[0]}",
                ),
                html.Div(
                    style={"margin-bottom": "30px"},
                    children=[
                        dcc.Slider(
                            id=self.xline_slider_id,
                            min=self.xtgeo_source.xlines[0],
                            max=self.xtgeo_source.xlines[-1],
                            value=self.xtgeo_source.xlines[0],
                            updatemode='drag',
                            marks={
                                i: i for i in range(self.xline_count) if i % 50 == 0
                            },
                        )
                    ],
                ),
                LayeredMap(id=self.xline_map_id, layers=[], height=400),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 3fr"),
            children=[
                self.slice_layout,
                html.Div(children=[self.iline_layout, self.xline_layout]),
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

            # idx = depth
            # print("depth index", idx)
            # depth_arr = self.source.depth_slice[0].T.copy()
            # print('segyio', depth_arr)
            # print(depth_arr, 'segyio')
            idx = np.where(self.xtgeo_source.zslices == depth)
            depth_arr = self.xtgeo_source.values[:, :, idx]
            # print(idx)
            # print(depth_arr)
            depth_arr = depth_arr[:,:,0,0].T
            print('xtgeo', depth_arr)
            bounds = [[0, 0], [self.xline_count - 1, self.iline_count - 1]]
            layer = generate_layer("Depth", depth_arr, bounds=bounds, colormap="RdBu")
            return (f"Depth {depth}", [layer])

        @app.callback(
            [
                Output(self.iline_label_id, "children"),
                Output(self.iline_map_id, "layers"),
            ],
            [Input(self.iline_slider_id, "value")],
        )
        def set_iline(iline):
            if not iline:
                raise PreventUpdate
            idx = np.where(self.xtgeo_source.ilines == iline)
            iline_arr = self.xtgeo_source.values[idx, :, :][0, 0, :].T
            bounds = [[0, 0], [self.iline_count - 1, self.sample_count - 1]]
            layer = generate_layer("inline", iline_arr, bounds=bounds, colormap="RdBu")
            return (f"Inline {iline}", [layer])

        @app.callback(
            [
                Output(self.xline_label_id, "children"),
                Output(self.xline_map_id, "layers"),
            ],
            [Input(self.xline_slider_id, "value")],
        )
        def set_xline(xline):
            if not xline:
                raise PreventUpdate
            idx = np.where(self.xtgeo_source.xlines == xline)
            xline_arr = self.xtgeo_source.values[:,idx, :][:, 0, 0].T
            bounds = [[0, 0], [self.xline_count - 1, self.sample_count - 1]]
            layer = generate_layer("inline", xline_arr, bounds=bounds, colormap="RdBu")
            return f"Crossline {xline}", [layer]

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
