from uuid import uuid4
from pathlib import Path
from typing import List

import numpy as np
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore

from ..datainput._xsection import XSectionFigure
from ..datainput._seismic import load_cube_data
from ..datainput._well import load_well
from ..datainput._surface import load_surface, get_surface_arr
from ..datainput._image_processing import array_to_png, get_colormap


class FenceViewer(WebvizContainerABC):
    """### SeismicFence



* `segyfiles`: List of file paths to segyfiles
* `surfacenames`: List of file paths to surfaces
* `wellfiles`: List of file paths to surfaces
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        surfacefiles: List[Path],
        wellfiles: List[Path],
        segyfiles: List[Path] = None,
        surfacenames: list = None,
        zonelog: str = None,
        zunit="depth (m)",
        zonecolors: list = None,
        zmin: float = None,
        zmax: float = None,
        zonemin: int = 1,
        nextend: int = 1,
        sampling: int = 100,
    ):
        self.zunit = zunit
        self.sampling = sampling
        self.nextend = nextend
        self.zmin = zmin
        self.zmax = zmax
        self.zonemin = zonemin
        self.surfacenames = surfacenames
        self.surfacefiles = [str(surface) for surface in surfacefiles]
        self.wellfiles = [str(well) for well in wellfiles]
        self.segyfiles = [str(segy) for segy in segyfiles] if segyfiles else []
        self.surfacenames = (
            surfacenames if surfacenames else [surface.stem for surface in surfacefiles]
        )
        self.zonelog = zonelog
        self.zonecolors = (
            zonecolors
            if zonecolors
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

    @property
    def well_layout(self):
        return html.Div(
            children=[
                html.Label(children="Well"),
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
        )

    @property
    def seismic_layout(self):
        return html.Div(
            style={} if self.segyfiles else {"display": "none"},
            children=[
                html.Label(children="Seismic"),
                dcc.Dropdown(
                    id=self.ids("cube"),
                    options=[
                        {"label": Path(segy).stem, "value": segy}
                        for segy in self.segyfiles
                    ]
                    if self.segyfiles
                    else None,
                    value=self.segyfiles[0] if self.segyfiles else None,
                    clearable=False,
                ),
            ],
        )

    @property
    def options_layout(self):
        return dcc.Checklist(
            id=self.ids("options"),
            options=[
                self.segyfiles and {"label": "Show seismic", "value": "show_seismic"},
                {"label": "Show surface fill", "value": "show_surface_fill",},
                self.zonelog and {"label": "Show zonelog", "value": "show_zonelog"},
            ],
            value=["show_surface_fill", "show_zonelog"],
        )

    @property
    def layout(self):
        return html.Div(
            # style=self.set_grid_layout("1fr 3fr"),
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 1fr 1fr 1fr"),
                    children=[
                        self.well_layout,
                        self.seismic_layout,
                        self.options_layout,
                        html.Button(id=self.ids("show_map"), children="Show map",),
                    ],
                ),
                html.Div(
                    id=self.ids("viz_wrapper"),
                    style={"position": "relative"},
                    children=[
                        html.Div(
                            id=self.ids("map_wrapper"),
                            style={
                                "position": "absolute",
                                "width": "30%",
                                "height": "40%",
                                "right": 0,
                                "zIndex": 10000,
                                "visibility": "hidden",
                            },
                            children=LayeredMap(
                                height=400, id=self.ids("map"), layers=[]
                            ),
                        ),
                        wcc.Graph(id=self.ids("graph")),
                    ],
                ),
            ],
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
                Input(self.ids("wells"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("options"), "value"),
            ],
        )
        def _render_section(well, cube, options):
            well = load_well(str(get_path(well)))
            xsect = XSectionFigure(
                well=well,
                zmin=self.zmin,
                zmax=self.zmax,
                nextend=self.nextend,
                sampling=self.sampling,
            )

            surfaces = [load_surface(str(get_path(surf))) for surf in self.surfacefiles]

            xsect.plot_surfaces(
                surfaces=surfaces,
                surfacenames=self.surfacenames,
                fill="show_surface_fill" in options,
            )

            if "show_seismic" in options:
                cube = load_cube_data(str(get_path(cube)))
                xsect.plot_cube(cube)

            xsect.plot_well(
                zonelogname=self.zonelog if "show_zonelog" in options else None,
                zonemin=self.zonemin,
            )
            return {"data": xsect.data, "layout": xsect.layout}

        @app.callback(
            [
                Output(self.ids("map_wrapper"), "style"),
                Output(self.ids("show_map"), "children"),
            ],
            [Input(self.ids("show_map"), "n_clicks")],
            [State(self.ids("map_wrapper"), "style")],
        )
        def _show_map(nclicks, style):
            btn = "Show Map"
            if not nclicks:
                raise PreventUpdate
            if nclicks % 2:
                style["visibility"] = "visible"
                btn = "Hide Map"
            else:
                style["visibility"] = "hidden"
            return style, btn

        @app.callback(
            [Output(self.ids("map"), "layers"), Output(self.ids("map"), "uirevision")],
            [Input(self.ids("wells"), "value")],
        )
        def _render_surface(wellname):
            wellname = get_path(wellname)
            surface = load_surface(str(get_path(self.surfacefiles[0])))
            well = load_well(str(wellname))
            arr = get_surface_arr(surface)
            s_layer = make_surface_layer(
                arr, name=self.surfacenames[0], hillshading=True,
            )
            well_layer = make_well_layer(well, wellname.stem)
            return [s_layer, well_layer], "keep"

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": fn}]) for fn in self.segyfiles],
            *[(get_path, [{"path": fn}]) for fn in self.surfacefiles],
            *[(get_path, [{"path": fn}]) for fn in self.wellfiles],
        ]


@webvizstore
def get_path(path) -> Path:
    return Path(path)


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
        "name": name,
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


def make_well_layer(well, name="well", zmin=0):

    well.dataframe = well.dataframe[well.dataframe["Z_TVDSS"] > zmin]
    positions = well.dataframe[["X_UTME", "Y_UTMN"]].values
    return {
        "name": name,
        "checked": True,
        "base_layer": False,
        "data": [
            {
                "type": "polyline",
                "color": "black",
                # "metadata": {"type": "well", "name": name},
                "positions": positions,
                "tooltip": name,
            }
        ],
    }
