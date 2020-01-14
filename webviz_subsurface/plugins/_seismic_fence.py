from uuid import uuid4
from pathlib import Path
import json
import numpy as np
import pandas as pd

from matplotlib.colors import ListedColormap
import xtgeo
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc

# pylint: disable=no-name-in-module
from dash_colorscales import DashColorscales
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LayeredMap

from .._datainput.seismic import load_cube_data
from .._datainput.surface import get_surface_arr, make_surface_layer, get_surface_fence
from .._datainput.image_processing import array_to_png, get_colormap


class SeismicFence(WebvizPluginABC):
    """### SeismicFence



* `segyfiles`: List of file paths to segyfiles
* `surfacefiles`: List of file paths to surfaces
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    def __init__(
        self,
        app,
        segyfiles: list,
        surfacefiles: list,
        zunit="depth (m)",
        colors: list = None,
    ):

        super().__init__()
        self.zunit = zunit
        self.segyfiles = segyfiles
        self.surfacefiles = surfacefiles
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
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    # @property
    # def tour_steps(self):
    #     return [
    #         {"id": self.ids('cube'), "content": ("The currently visualized seismic cube.")},
    #         {
    #             "id": self.iline_map_id,
    #             "content": (
    #                 "Selected inline for the seismic cube. "
    #                 "Adjacent views are updated by clicking MB1 "
    #                 "in the plot. To zoom, hold MB1 and draw a vertical/horizontal "
    #                 "line or a rectangle."
    #             ),
    #         },
    #         {
    #             "id": self.xline_map_id,
    #             "content": ("Selected crossline for the seismic cube "),
    #         },
    #         {
    #             "id": self.zline_map_id,
    #             "content": ("Selected zslice for the seismic cube "),
    #         },
    #         {
    #             "id": self.ids('color-scale'),
    #             "content": ("Click this button to change colorscale"),
    #         },
    #         {
    #             "id": self.ids('color-values'),
    #             "content": ("Drag either node of slider to truncate color ranges"),
    #         },
    #         {
    #             "id": self.ids('color-range-btn'),
    #             "content": (
    #                 "Click this button to update color slider min/max and reset ranges."
    #             ),
    #         },
    #         {
    #             "id": self.zoom_btn,
    #             "content": ("Click this button to reset zoom/pan state in the plot"),
    #         },
    #     ]

    @property
    def surface_layout(self):
        """Layout for surface section"""
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 1fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={"textAlign": "center"},
                                    children="Select surface",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("surface"),
                                    options=[
                                        {"label": Path(cube).stem, "value": cube}
                                        for cube in self.surfacefiles
                                    ],
                                    value=self.surfacefiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            style={"marginRight": "50px", "marginLeft": "50px"},
                            children=[
                                html.Label(
                                    style={"textAlign": "center"}, children="Display as"
                                ),
                                dcc.RadioItems(
                                    id=self.ids("surface-type"),
                                    options=[
                                        {"label": "Surface", "value": "surface"},
                                        {
                                            "label": "Seismic attribute",
                                            "value": "attribute",
                                        },
                                    ],
                                    value="surface",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={"height": "800px", "zIndex": -9999},
                            children=LayeredMap(
                                id=self.ids("map-view"),
                                draw_toolbar_polyline=True,
                                hillShading=True,
                                layers=[],
                            ),
                        )
                    ]
                ),
            ]
        )

        return

    @property
    def seismic_layout(self):
        """Layout for color and other settings"""
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("3fr 2fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={"textAlign": "center"},
                                    children="Select seismic cube",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("cube"),
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
                                    style={"textAlign": "center"},
                                    children="Set colorscale",
                                ),
                                DashColorscales(
                                    id=self.ids("color-scale"),
                                    colorscale=self.initial_colors,
                                    nSwatches=12,
                                ),
                            ],
                        ),
                        html.Div(
                            style={"marginRight": "50px", "marginLeft": "50px"},
                            children=[
                                html.Label(
                                    style={"textAlign": "center"},
                                    children="Set color range",
                                ),
                                dcc.RangeSlider(
                                    id=self.ids("color-values"),
                                    tooltip={"always_visible": True},
                                ),
                            ],
                        ),
                        html.Button(
                            id=self.ids("color-range-btn"), children="Reset Range"
                        ),
                    ],
                ),
                html.Div(
                    style={"height": "800px"},
                    children=wcc.Graph(
                        config={"displayModeBar": False}, id=self.ids("fence-view")
                    ),
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[self.surface_layout, self.seismic_layout],
        )

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("surface"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
            ],
        )
        def render_surface(
            surfacepath, surface_type, cubepath, color_values, colorscale
        ):
            surface = xtgeo.RegularSurface(str(get_path(surfacepath)), cubepath)
            hillshading = True
            min_val = None
            max_val = None
            color = "viridis"

            if surface_type == "attribute":
                hillshading = False
                min_val = color_values[0] if color_values else None
                max_val = color_values[1] if color_values else None
                color = ListedColormap(colorscale) if colorscale else "viridis"
                cube = load_cube_data(get_path(cubepath))
                surface.slice_cube(cube)
                surface.values = surface.values.filled(0)

            s_layer = make_surface_layer(
                surface,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            return [s_layer]

        @app.callback(
            Output(self.ids("fence-view"), "figure"),
            [
                Input(self.ids("map-view"), "polyline_points"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("surface"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
            ],
        )
        def render_fence(coords, cubepath, surfacepath, color_values, colorscale):
            if not coords:
                raise PreventUpdate
            cube = load_cube_data(get_path(cubepath))
            fence = get_fencespec(coords)
            hmin, hmax, vmin, vmax, values = cube.get_randomline(fence)
            surface = xtgeo.RegularSurface(str(get_path(surfacepath)), cubepath)
            s_arr = get_surface_fence(fence, surface)
            return make_heatmap(
                values,
                s_arr=s_arr,
                colorscale=colorscale,
                xmin=hmin,
                xmax=hmax,
                ymin=vmin,
                ymax=vmax,
                zmin=color_values[0],
                zmax=color_values[1],
                xaxis_title="Distance along fence",
                yaxis_title=self.zunit,
            )
            raise PreventUpdate

        @app.callback(
            [
                Output(self.ids("color-values"), "min"),
                Output(self.ids("color-values"), "max"),
                Output(self.ids("color-values"), "value"),
                Output(self.ids("color-values"), "step"),
            ],
            [Input(self.ids("color-range-btn"), "n_clicks")],
            [State(self.ids("cube"), "value")],
        )
        def update_color_slider(clicks, cubepath):
            cube = load_cube_data(get_path(cubepath))

            minv = float(f"{round(cube.values.min(), 2):2f}")
            maxv = float(f"{round(cube.values.max(), 2):2f}")
            value = [minv, maxv]
            step = (maxv - minv) / 100
            return minv, maxv, value, step

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": fn}]) for fn in self.segyfiles],
            *[(get_path, [{"path": fn}]) for fn in self.surfacefiles],
        ]


# pylint: disable=too-many-arguments
def make_heatmap(
    arr,
    s_arr,
    s_color="black",
    s_name=None,
    height=800,
    zmin=None,
    zmax=None,
    xmin=None,
    xmax=None,
    ymin=None,
    ymax=None,
    colorscale=None,
    uirevision=None,
    showscale=True,
    reverse_y=True,
    xaxis=None,
    yaxis=None,
    text=None,
    title=None,
    yaxis_title=None,
    xaxis_title=None,
):

    x_inc = (xmax - xmin) / arr.shape[1]
    y_inc = (ymax - ymin) / arr.shape[0]
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
                "x0": xmin,
                "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                "showscale": showscale,
                "colorscale": colors,
                "zmin": zmin,
                "zmax": zmax,
            },
            {
                "type": "line",
                "y": s_arr[:, 2],
                "x": s_arr[:, 3],
                "marker": {"color": s_color},
            },
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


def get_fencespec(coords):
    """Create a XTGeo fence spec from polyline coordinates"""
    coords_dict = [{"X_UTME": c[1], "Y_UTMN": c[0], "Z_TVDSS": 0} for c in coords]
    df = pd.DataFrame().from_dict(coords_dict)
    df["POLY_ID"] = 1
    df["NAME"] = "test"
    poly = xtgeo.Polygons()
    poly.dataframe = df
    return poly.get_fence(asnumpy=True)
