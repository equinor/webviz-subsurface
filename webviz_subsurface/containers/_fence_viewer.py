from uuid import uuid4
from pathlib import Path
from typing import List

from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizContainerABC
from webviz_config.webviz_store import webvizstore

from ..datainput._xsection import XSectionFigure
from ..datainput._seismic import load_cube_data
from ..datainput._well import load_well
from ..datainput._surface import load_surface


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
    ):
        self.zunit = zunit
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
            style=not self.segyfiles and {"display": "none"},
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
                    style=self.set_grid_layout("1fr 1fr 1fr"),
                    children=[
                        self.well_layout,
                        self.seismic_layout,
                        self.options_layout,
                    ],
                ),
                wcc.Graph(id=self.ids("graph")),
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
        def _render_surface(well, cube, options):
            well = load_well(str(get_path(well)))
            xsect = XSectionFigure(
                well=well, zmin=self.zmin, zmax=self.zmax, nextend=50
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

    def add_webvizstore(self):
        return [
            *[(get_path, [{"path": fn}]) for fn in self.segyfiles],
            *[(get_path, [{"path": fn}]) for fn in self.surfacefiles],
            *[(get_path, [{"path": fn}]) for fn in self.wellfiles],
        ]


@webvizstore
def get_path(path) -> Path:
    return Path(path)
