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
from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LayeredMap

from ..datainput._seismic import load_cube_data, get_iline, get_xline, get_zslice
from ..datainput._surface import get_surface_arr, get_surface_fence
from ..datainput.layeredmap._image_processing import array_to_png, get_colormap


class SeismicFence(WebvizContainerABC):
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
        wellfiles: list = None,
        zunit="depth (m)",
        colors: list = None,
    ):
        self.zunit = zunit
        self.segyfiles = segyfiles
        self.surfacefiles = surfacefiles
        self.wells = wellfiles
        self.wellfiles = [get_path(Path(fn)) for fn in wellfiles] if wellfiles else None
        print('asdasdasdasd',self.wellfiles)
        self.welllayers = make_well_layers(self.wellfiles)
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
        self.make_uuids()
        self.set_callbacks(app)

    def make_uuids(self):
        uuid = f"{uuid4()}"
        self.cube_id = f"cube_id-{uuid}"
        self.surface_id = f"surface_id-{uuid}"
        self.surface_type_id = f"surface_type_id-{uuid}"
        self.map_id = f"map_id-{uuid}"
        self.fence_id = f"fence_id-{uuid}"
        self.color_values_id = f"color_values_id-{uuid}"
        self.color_scale_id = f"color_scale_id-{uuid}"
        self.color_range_btn = f"color_range_btn-{uuid}"
        self.zoom_btn = f"zoom_btn-{uuid}"
        self.state_store = f"state_store-{uuid}"

    # @property
    # def tour_steps(self):
    #     return [
    #         {"id": self.cube_id, "content": ("The currently visualized seismic cube.")},
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
    #             "id": self.color_scale_id,
    #             "content": ("Click this button to change colorscale"),
    #         },
    #         {
    #             "id": self.color_values_id,
    #             "content": ("Drag either node of slider to truncate color ranges"),
    #         },
    #         {
    #             "id": self.color_range_btn,
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
                                    id=self.surface_id,
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
                                    id=self.surface_type_id,
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
                                id=self.map_id,
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
                                    style={"textAlign": "center"},
                                    children="Set colorscale",
                                ),
                                DashColorscales(
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
                                    style={"textAlign": "center"},
                                    children="Set color range",
                                ),
                                dcc.RangeSlider(
                                    id=self.color_values_id,
                                    tooltip={"always_visible": True},
                                ),
                            ],
                        ),
                        html.Button(id=self.color_range_btn, children="Reset Range"),
                        # html.Button(id=self.zoom_btn, children="Reset zoom"),
                    ],
                ),
                html.Div(
                    style={"height": "800px"},
                    children=wcc.Graph(
                        config={"displayModeBar": False}, id=self.fence_id
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
            [Output(self.map_id, "layers"), Output(self.map_id, "uirevision")],
            [
                Input(self.surface_id, "value"),
                Input(self.surface_type_id, "value"),
                Input(self.cube_id, "value"),
                Input(self.color_values_id, "value"),
                Input(self.color_scale_id, "colorscale"),
            ],
        )
        def render_surface(
            surfacepath, surface_type, cubepath, color_values, colorscale
        ):
            surface = xtgeo.RegularSurface(str(get_path(Path(surfacepath))), cubepath)
            hillshading = True
            min_val = None
            max_val = None
            color = "viridis"

            if surface_type == "attribute":
                hillshading = False
                min_val = color_values[0] if color_values else None
                max_val = color_values[1] if color_values else None
                color = ListedColormap(colorscale) if colorscale else "viridis"
                cube = load_cube_data(get_path(Path(cubepath)))
                surface.slice_cube(cube)

            arr = get_surface_arr(surface)
            s_layer = make_surface_layer(
                arr,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            # layers = self.welllayers.extend(s_layer)

            return [s_layer, *self.welllayers], "keep"

        @app.callback(
            Output(self.fence_id, "figure"),
            [
                Input(self.map_id, "polyline_points"),
                Input(self.cube_id, "value"),
                Input(self.surface_id, "value"),
                Input(self.color_values_id, "value"),
                Input(self.color_scale_id, "colorscale"),
            ],
        )
        def render_fence(coords, cubepath, surfacepath, color_values, colorscale):
            if not coords:
                raise PreventUpdate
            cube = load_cube_data(get_path(Path(cubepath)))
            fence = get_fencespec(coords)
            hmin, hmax, vmin, vmax, values = cube.get_randomline(fence)
            surface = xtgeo.RegularSurface(str(get_path(Path(surfacepath))), cubepath)
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
                Output(self.color_values_id, "min"),
                Output(self.color_values_id, "max"),
                Output(self.color_values_id, "value"),
                Output(self.color_values_id, "step"),
            ],
            [Input(self.color_range_btn, "n_clicks")],
            [State(self.cube_id, "value")],
        )
        def update_color_slider(clicks, cubepath):
            cube = load_cube_data(get_path(Path(cubepath)))

            minv = float(f"{round(cube.values.min(), 2):2f}")
            maxv = float(f"{round(cube.values.max(), 2):2f}")
            value = [minv, maxv]
            step = (maxv - minv) / 100
            return minv, maxv, value, step

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": Path(fn)}]) for fn in self.segyfiles],
            *[(get_path, [{"path": Path(fn)}]) for fn in self.surfacefiles],
            *[(get_path, [{"path": Path(fn)}]) for fn in self.wells],
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


def make_surface_layer(
    arr,
    name="surface",
    min_val=None,
    max_val=None,
    color="viridis",
    hillshading=False,
    unit="m",
):
    bounds = [[np.min(arr[0]), np.min(arr[1])], [np.max(arr[0]), np.max(arr[1])]]
    min_val = min_val if min_val else np.min(arr[2])
    max_val = max_val if min_val else np.max(arr[2])
    return {
        "name": "surface",
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(arr[2].copy()),
                "colormap": get_colormap(color),
                "bounds": bounds,
                "allowHillshading": hillshading,
                "minvalue": f"{min_val:.2f}" if min_val else None,
                "maxvalue": f"{max_val:.2f}" if max_val else None,
                "unit": unit,
            }
        ],
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


def make_well_layer(fn, zmin=0):

    # reduce the well data by Pandas operations
    wo = xtgeo.Well(fn)
    wo.dataframe = wo.dataframe[wo.dataframe["Z_TVDSS"] > zmin]
    positions = wo.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": Path(fn).stem,
        "checked": True,
        "base_layer": False,
        "data": [
            {
                "type": "polyline",
                "color": "black",
                "tooltip": Path(fn).stem,
                # "metadata": {"type": "well", "name": name},
                "positions": positions,
            }
        ],
    }
    # # Create a relative XYLENGTH vector (0.0 where well starts)
    # wo.create_relative_hlen()
    # dfr = wo.dataframe

    # # get the well trajectory (numpies) as copy
    # zv = dfr["Z_TVDSS"].values.copy()
    # hv = dfr["R_HLEN"].values.copy()
    # zv_copy = np.ma.masked_where(zv < zmin, zv)
    # hv_copy = np.ma.masked_where(zv < zmin, hv)
    # return zv_copy, hv_copy


def make_well_layers(wellpaths):
    
    
    return [make_well_layer(fn) for fn in wellpaths]
