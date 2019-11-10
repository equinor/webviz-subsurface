from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd

import segyio
import xtgeo

from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
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
        self.xtgeo_source = xtgeo.Cube(segyfile)
        self.iline_count = len(self.xtgeo_source.ilines)
        self.xline_count = len(self.xtgeo_source.xlines)
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
                            updatemode="drag",
                            step=self.xtgeo_source.zinc,
                        )
                    ],
                ),
                html.Div(
                    style={"height": "876px"}, children=wcc.Graph(id=self.depth_map_id)
                ),
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
                            max=self.xtgeo_source.ilines[-1],
                            value=self.xtgeo_source.ilines[0],
                            updatemode="drag",
                        )
                    ],
                ),
                html.Div(
                    style={"height": "400px"}, children=wcc.Graph(id=self.iline_map_id)
                ),
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
                            updatemode="drag",
                        )
                    ],
                ),
                html.Div(
                    style={"height": "400px"}, children=wcc.Graph(id=self.xline_map_id)
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 2fr"),
            children=[
                self.slice_layout,
                html.Div(children=[self.iline_layout, self.xline_layout]),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.depth_label_id, "children"),
                Output(self.depth_map_id, "figure"),
            ],
            [Input(self.depth_slider_id, "value")],
        )
        def set_depth(depth):
            print(depth)
            if not depth:
                raise PreventUpdate

            idx = np.where(self.xtgeo_source.zslices == depth)
            depth_arr = self.xtgeo_source.values[:, :, idx]
            depth_arr = depth_arr[:, :, 0, 0].T
            print("xtgeo", depth_arr)
            return (f"Depth {depth}", make_heatmap(depth_arr))

        @app.callback(
            [
                Output(self.iline_label_id, "children"),
                Output(self.iline_map_id, "figure"),
            ],
            [Input(self.iline_slider_id, "value")],
        )
        def set_iline(iline):
            if not iline:
                raise PreventUpdate
            idx = np.where(self.xtgeo_source.ilines == iline)
            iline_arr = self.xtgeo_source.values[idx, :, :][0, 0, :].T
            return (f"Inline {iline}", make_heatmap(iline_arr))

        @app.callback(
            [
                Output(self.xline_label_id, "children"),
                Output(self.xline_map_id, "figure"),
            ],
            [Input(self.xline_slider_id, "value")],
        )
        def set_xline(xline):
            if not xline:
                raise PreventUpdate
            idx = np.where(self.xtgeo_source.xlines == xline)
            xline_arr = self.xtgeo_source.values[:, idx, :][:, 0, 0].T
            return f"Crossline {xline}", make_heatmap(xline_arr)

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




def make_heatmap(arr, reverse_y=True):
    return {
        "data": [
            {
                "type": "heatmap",
                "z": arr.tolist(),
                # "x0": hmin,
                # "xmax": hmax,
                # "dx": x_inc,
                # "y0": vmin,
                # "ymax": vmax,
                # "dy": y_inc,
                "zsmooth": "best",
            }
        ],
        "layout": {
            "margin": {"t": 0},
            "yaxis": {"autorange": "reversed" if reverse_y else None},
        },
    }
