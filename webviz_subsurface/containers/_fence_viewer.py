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

from ..datainput._xsection import XSection


class FenceViewer(WebvizContainerABC):
    """### SeismicFence



* `segyfiles`: List of file paths to segyfiles
* `surfacenames`: List of file paths to surfaces
* `wellfiles`: List of file paths to surfaces
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    def __init__(
        self,
        app,
        # segyfiles: list,
        surfacepath: Path,
        surfacenames: list,
        surfaceattribute: str,
        segyfiles: list = None,
        wellfiles: list = None,
        zunit="depth (m)",
        colors: list = None,
    ):
        self.zunit = zunit
        self.surfacenames = surfacenames
        self.surfaceattribute = surfaceattribute
        self.surfacepath = surfacepath
        self.segyfiles = segyfiles
        self.wellfiles = wellfiles if wellfiles else []

        # self.welllayers = make_well_layers(self.wellfiles)
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
                    # style=self.set_grid_layout("1fr 1fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                          
                                    children="Select surface",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("surfacename"),
                                    options=[
                                        {"label": Path(cube).stem, "value": cube}
                                        for cube in self.surfacenames
                                    ],
                                    value=self.surfacenames[0],
                                    multi=True,
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            
                            children=[
                                html.Label(
                                     children="Well"
                                ),
                                dcc.Dropdown(
                                    id=self.ids("wells"),
                                    options=[
                                        {"label": Path(well).stem, "value": well}
                                        for well in self.wellfiles
                                    ],
                                    value=self.wellfiles[0],
                                    clearable=False,
                                ),
                            ],
                        ),
                        html.Div(
                            
                            children=[
                                html.Label(
                                   children="Well"
                                ),
                                dcc.Dropdown(
                                    id=self.ids("cube"),
                                    options=[
                                        {"label": Path(segy).stem, "value": segy}
                                        for segy in self.segyfiles
                                    ],
                                    value=self.segyfiles[0],
                                    clearable=False,
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        return

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 3fr"),
            children=[self.surface_layout, wcc.Graph(id=self.ids("graph"))],
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
            Output(self.ids("graph"), "figure"),
            [
                Input(self.ids("surfacename"), "value"),
                Input(self.ids("wells"), "value"),
                Input(self.ids("cube"), "value"),
            ],
        )
        def render_surface(surfacenames, well, cube):
            well = xtgeo.Well(well)
            xsect = XSection(well=well, nextend=50)

            if surfacenames:
                surfaces = load_surfaces(self.surfacepath, self.surfacenames, self.surfaceattribute)
                xsect.plot_surfaces(surfaces=surfaces, fill=False)

            cube = xtgeo.Cube(str(get_path(cube)))
            
            xsect.plot_well(zonelogname="Zonelog", facieslogname="Faciesfg")
            
            xsect.plot_cube(cube)

            return {"data": xsect.data, "layout": xsect.layout}

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": fn}]) for fn in self.segyfiles],
            *[(get_path, [{"path": fn}]) for fn in self.surfacenames],
            *[(get_path, [{"path": fn}]) for fn in self.wellfiles],
        ]


def load_surfaces(surfacepath, surfacenames, surfaceattribute):
    surfacenames = (
                surfacenames if isinstance(surfacenames, list) else [surfacenames]
            )
    return [
        xtgeo.RegularSurface(
            str(get_path(surfacepath / f"{name}--{surfaceattribute}.gri"))
        )
        for name in surfacenames
    ]


@webvizstore
def get_path(path) -> Path:
    return Path(path)
