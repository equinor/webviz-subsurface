from uuid import uuid4
from pathlib import Path
import json

import numpy as np
import pandas as pd

import segyio
import xtgeo

import dash
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
import dash_colorscales

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

    def __init__(self, app, segyfiles: list, zunit="depth", colors: list = None):

        self.cube_id = "cube-id-{}".format(uuid4())
        self.iline_map_id = "iline-map-id-{}".format(uuid4())
        self.xline_map_id = "xline-map-id-{}".format(uuid4())
        self.zline_map_id = "zline-map-id-{}".format(uuid4())
        self.value_distr_id = "value-distr-id-{}".format(uuid4())
        self.color_values_id = "color_values-id-{}".format(uuid4())
        self.color_scale_id = f"{str(uuid4())}-color-scale-id"
        self.color_range_btn = f"{str(uuid4())}-color-range-id"
        self.zoom_btn = f"{str(uuid4())}-zoom-id"
        self.state_store = "state-store-id-{}".format(uuid4())
        self.zunit = zunit
        self.segyfiles = segyfiles

        self.initial_colors = (
            colors
            if colors
            else [
                "#67001f",
                "#ab152a",
                "#d05546",
                "#ec9372",
                "#fac8ac",
                "#faeae1",
                "#e6eff4",
                "#bbd9e9",
                "#7db7d6",
                "#3a8bbf",
                "#1f61a5",
                "#053061",
            ]
        )
        self.init_state = self.update_state(segyfiles[0])
        self.init_state.get("colorscale", self.initial_colors)
        self.init_state.get("uirevision", str(uuid4()))

        self.set_callbacks(app)

    def update_state(self, cubepath, **kwargs):
        cube = load_cube_data(get_path(Path(cubepath)))
        state = {
            "cubepath": cubepath,
            "iline": int(cube.ilines[0]),
            "xline": int(cube.xlines[0]),
            "zslice": float(cube.zslices[0]),
            "min_value": float(f"{round(cube.values.min(), 2):2f}"),
            "max_value": float(f"{round(cube.values.max(), 2):2f}"),
            "color_min_value": float(f"{round(cube.values.min(), 2):2f}"),
            "color_max_value": float(f"{round(cube.values.max(), 2):2f}"),
            "uirevision": str(uuid4()),
            "colorscale": self.initial_colors,
        }
        if kwargs:
            for key, value in kwargs:
                state[key] = valu
        return state

    @property
    def settings_layout(self):
        """Layout for color and other settings"""
        return html.Div(
            style=self.set_grid_layout("3fr 2fr 5fr 1fr 1fr"),
            children=[
                html.Div(
                    children=[
                        html.Label(
                            style={"textAlign": "center"},
                            children="Select seismic cube",
                        ),
                        dcc.Dropdown(
                            id=self.cube_id,
                            options=[
                                {"label": Path(cube).stem, "value": cube}
                                for cube in self.segyfiles
                            ],
                            value=self.segyfiles[0],
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    style={"zIndex": 2000},
                    children=[
                        html.Label(
                            style={"textAlign": "center"}, children="Set colorscale"
                        ),
                        dash_colorscales.DashColorscales(
                            id=self.color_scale_id,
                            colorscale=self.initial_colors,
                            nSwatches=12,
                        ),
                    ],
                ),
                html.Div(
                    style={"marginRight": "50px", "marginLeft": "50px"},
                    children=[
                        html.Label(
                            style={"textAlign": "center"}, children="Set color range"
                        ),
                        dcc.RangeSlider(
                            id=self.color_values_id,
                            min=self.init_state["min_value"],
                            max=self.init_state["max_value"],
                            value=[
                                self.init_state["min_value"],
                                self.init_state["max_value"],
                            ],
                            tooltip={"always_visible": True},
                            step=(
                                self.init_state["max_value"]
                                - self.init_state["min_value"]
                            )
                            / 100,
                        )
                    ],
                ),
                html.Button(id=self.color_range_btn, children="Reset Range"),
                html.Button(id=self.zoom_btn, children="Reset zoom"),
            ],
        )

    @property
    def plot_layout(self):
        """Layout for main plots"""
        return html.Div(
            style=self.set_grid_layout("2fr 1fr"),
            children=[
                html.Div(
                    children=[
                        html.Div(
                            style={"height": "400px"},
                            children=wcc.Graph(
                                config={"displayModeBar": False}, id=self.iline_map_id
                            ),
                        ),
                        html.Div(
                            style={"height": "400px"},
                            children=wcc.Graph(
                                config={"displayModeBar": False}, id=self.xline_map_id
                            ),
                        ),
                    ]
                ),
                html.Div(
                    style={"height": "876px"},
                    children=wcc.Graph(
                        config={"displayModeBar": False}, id=self.zline_map_id
                    ),
                ),
                dcc.Store(id=self.state_store, data=json.dumps(self.init_state)),
            ],
        )

    @property
    def layout(self):
        return html.Div(children=[self.settings_layout, self.plot_layout])

    def set_callbacks(self, app):
        @app.callback(
            Output(self.state_store, "data"),
            [
                Input(self.cube_id, "value"),
                Input(self.iline_map_id, "clickData"),
                Input(self.xline_map_id, "clickData"),
                Input(self.zline_map_id, "clickData"),
                Input(self.color_values_id, "value"),
                Input(self.color_scale_id, "colorscale"),
                Input(self.zoom_btn, "n_clicks"),
                Input(self.color_range_btn, "n_clicks"),
            ],
            [State(self.zline_map_id, "figure"), State(self.state_store, "data")],
        )
        def update_state(
            cubepath,
            icd,
            xcd,
            zcd,
            color_values,
            colorscale,
            zoom_btn,
            reset_range_btn,
            zfig,
            store,
        ):
            """Updates dcc.Store object with active iline, xline, zlayer and color settings.
            """
            store = json.loads(store)
            ctx = dash.callback_context.triggered[0]["prop_id"]
            x_was_clicked = (
                xcd if xcd and ctx == f"{self.xline_map_id}.clickData" else None
            )
            i_was_clicked = (
                icd if icd and ctx == f"{self.iline_map_id}.clickData" else None
            )
            z_was_clicked = (
                zcd if zcd and ctx == f"{self.zline_map_id}.clickData" else None
            )
            if ctx == f"{self.cube_id}.value":
                store = self.update_state(cubepath)
            if ctx == f"{self.zoom_btn}.n_clicks":
                store["uirevision"] = str(uuid4())
            if x_was_clicked:
                store["iline"] = xcd["points"][0]["x"]
                store["zslice"] = xcd["points"][0]["y"]
            if z_was_clicked:
                store["iline"] = zcd["points"][0]["x"]
                store["xline"] = zcd["points"][0]["y"]
                store["zslice"] = float(zfig["data"][0]["text"])
            if i_was_clicked:
                store["xline"] = icd["points"][0]["x"]
                store["zslice"] = icd["points"][0]["y"]
            if ctx == f"{self.color_range_btn}.n_clicks":
                store["color_min_value"] = store["min_value"]
                store["color_max_value"] = store["max_value"]
            else:
                store["color_min_value"] = color_values[0]
                store["color_max_value"] = color_values[1]
            store["colorscale"] = colorscale
            return json.dumps(store)

        @app.callback(
            Output(self.zline_map_id, "figure"), [Input(self.state_store, "data")]
        )
        def set_zslice(state):
            """Updates z-slice heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(state["cubepath"])
            shapes = [
                {
                    "type": "line",
                    "x0": state["iline"],
                    "y0": cube.xlines[0],
                    "x1": state["iline"],
                    "y1": cube.xlines[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "y0": state["xline"],
                    "x0": cube.ilines[0],
                    "y1": state["xline"],
                    "x1": cube.ilines[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]

            idx = np.where(cube.zslices == state["zslice"])
            zslice_arr = cube.values[:, :, idx]
            zslice_arr = zslice_arr[:, :, 0, 0].T
            fig = make_heatmap(
                zslice_arr,
                height=800,
                showscale=True,
                text=str(state["zslice"]),
                title=f'Zslice {state["zslice"]} ({self.zunit})',
                xaxis_title="Inline",
                yaxis_title="Crossline",
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            return fig

        @app.callback(
            Output(self.iline_map_id, "figure"), [Input(self.state_store, "data")]
        )
        def set_iline(state):
            """Updates inline heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(state["cubepath"])
            shapes = [
                {
                    "type": "line",
                    "x0": state["xline"],
                    "y0": cube.zslices[0],
                    "x1": state["xline"],
                    "y1": cube.zslices[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "x0": cube.xlines[0],
                    "y0": state["zslice"],
                    "x1": cube.xlines[-1],
                    "y1": state["zslice"],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]

            idx = np.where(cube.ilines == state["iline"])
            iline_arr = cube.values[idx, :, :][0, 0, :].T
            
            fig = make_heatmap(
                iline_arr,
                xaxis=cube.xlines,
                yaxis=cube.zslices,
                title=f'Inline {state["iline"]}',
                xaxis_title="Crossline",
                yaxis_title=self.zunit,
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            return fig

        @app.callback(
            Output(self.xline_map_id, "figure"), [Input(self.state_store, "data")]
        )
        def set_xline(state):
            """Update xline heatmap"""
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            cube = load_cube_data(state["cubepath"])
            shapes = [
                {
                    "type": "line",
                    "x0": state["iline"],
                    "y0": cube.zslices[0],
                    "x1": state["iline"],
                    "y1": cube.zslices[-1],
                    "line": {"width": 1, "dash": "dot"},
                },
                {
                    "type": "line",
                    "x0": cube.ilines[0],
                    "y0": state["zslice"],
                    "x1": cube.ilines[-1],
                    "y1": state["zslice"],
                    "line": {"width": 1, "dash": "dot"},
                },
            ]

            idx = np.where(cube.xlines == state["xline"])
            xline_arr = cube.values[:, idx, :][:, 0, 0].T
            fig = make_heatmap(
                xline_arr,
                xaxis=cube.ilines,
                yaxis=cube.zslices,
                title=f'Crossline {state["xline"]}',
                xaxis_title="Inline",
                yaxis_title=self.zunit,
                zmin=state["color_min_value"],
                zmax=state["color_max_value"],
                colorscale=state["colorscale"],
                uirevision=state["uirevision"],
            )
            fig["layout"]["shapes"] = shapes
            return fig

        @app.callback(
            [
                Output(self.color_values_id, "min"),
                Output(self.color_values_id, "max"),
                Output(self.color_values_id, "value"),
                Output(self.color_values_id, "step"),
            ],
            [Input(self.color_range_btn, "n_clicks")],
            [State(self.state_store, "data")],
        )
        def update_state(btn_clicked, state):
            if not state:
                raise PreventUpdate
            state = json.loads(state)
            minv = state["min_value"]
            maxv = state["max_value"]
            value = [minv, maxv]
            step = (maxv - minv) / 100
            return minv, maxv, value, step

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.segyfiles]


def make_heatmap(
    arr,
    height=400,
    zmin=None,
    zmax=None,
    colorscale=[],
    uirevision=None,
    showscale=False,
    reverse_y=True,
    xaxis=None,
    yaxis=None,
    text=None,
    title=None,
    yaxis_title=None,
    xaxis_title=None,
):
    """Createst heatmap plot"""
    colors = (
        [[i / (len(colorscale) - 1), color] for i, color in enumerate(colorscale)]
        if colorscale
        else "RdBu"
    )
    return {
        "data": [
            {
                "type": "heatmap",
                "text": text if text else None,
                "z": arr.tolist(),
                "x": xaxis,
                "y": yaxis,
                "zsmooth": "best",
                "showscale": showscale,
                "colorscale": colors,
                "zmin": zmin,
                "zmax": zmax,
            }
        ],
        "layout": {
            "height": height,
            "title": title,
            "uirevision": uirevision,
            "margin": {"b": 50, "t": 50, "r": 0},
            "yaxis": {
                "title": yaxis_title,
                "autorange": "reversed" if reverse_y else None,
            },
            "xaxis": {"title": xaxis_title},
        },
    }


@webvizstore
def get_path(path) -> Path:
    return Path(path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_cube_data(cube_path):
    return xtgeo.Cube(cube_path)
