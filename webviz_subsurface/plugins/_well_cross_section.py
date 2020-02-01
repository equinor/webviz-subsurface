from uuid import uuid4
from pathlib import Path
from typing import List

from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore

from .._datainput.xsection import XSectionFigure
from .._datainput.seismic import load_cube_data
from .._datainput.well import load_well, make_well_layer
from .._datainput.surface import load_surface, make_surface_layer


class WellCrossSection(WebvizPluginABC):
    """### WellCrossSection
    Displays a cross section along a well with intersected surfaces,
    and optionally seismic cubes.

* `segyfiles`: List of file paths to segyfiles
* `surfacefiles`: List of file paths to Irap binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `wellfiles`: List of file paths to RMS wells
* `zunit`: z-unit for display
* `zonelog`: Name of zonelog
* `zmin`: Visualized minimum z-value in cross section
* `zmax`: Visualized maximum z-value in cross section
* `zonemin`: First zonenumber to draw in log
* `sampling`: Sampling interval of well fence
* `nextend`: Number to extend distance of sampling, e.g. 2*20 (nextend*sampling)

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
        zmin: float = None,
        zmax: float = None,
        zonemin: int = 1,
        nextend: int = 2,
        sampling: int = 40,
    ):

        super().__init__()

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
        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def well_layout(self):
        return html.Div(
            children=html.Label(
                children=[
                    html.Span("Well:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("wells"),
                        options=[
                            {"label": Path(well).stem, "value": well}
                            for well in self.wellfiles
                        ],
                        value=self.wellfiles[0],
                        clearable=False,
                    ),
                ]
            ),
        )

    @property
    def seismic_layout(self):
        return html.Div(
            style={} if self.segyfiles else {"display": "none"},
            children=html.Label(
                children=[
                    html.Span("Seismic:", style={"font-weight": "bold"}),
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
                ]
            ),
        )

    @property
    def viz_options_layout(self):
        options = [{"label": "Show surface fill", "value": "show_surface_fill"}]
        value = ["show_surface_fill"]
        if self.segyfiles:
            options.append({"label": "Show seismic", "value": "show_seismic"})
        if self.zonelog:
            options.append({"label": "Show zonelog", "value": "show_zonelog"})
            value.append("show_zonelog")

        return dcc.Checklist(id=self.ids("options"), options=options, value=value,)

    @property
    def well_options(self):
        return html.Div(
            style={"marginLeft": "20px", "marginRight": "0px", "marginBotton": "0px"},
            children=[
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Sampling:", style={"font-weight": "bold"}),
                            dcc.Input(
                                id=self.ids("sampling"),
                                debounce=True,
                                type="number",
                                value=self.sampling,
                            ),
                        ]
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Nextend:", style={"font-weight": "bold"}),
                            dcc.Input(
                                id=self.ids("nextend"),
                                debounce=True,
                                type="number",
                                value=self.nextend,
                            ),
                        ]
                    )
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 1fr 1fr 1fr 1fr"),
                    children=[
                        self.well_layout,
                        self.well_options,
                        self.seismic_layout,
                        self.viz_options_layout,
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
                Input(self.ids("sampling"), "value"),
                Input(self.ids("nextend"), "value"),
            ],
        )
        def _render_section(well, cube, options, sampling, nextend):
            """Update cross section"""
            well = load_well(str(get_path(well)))
            xsect = XSectionFigure(
                well=well,
                zmin=self.zmin,
                zmax=self.zmax,
                nextend=int(nextend),
                sampling=int(sampling),
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
            xsect.layout["margin"] = {"t": 0}
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
            """Show/hide map on button click"""
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
        def _render_surface(wellfile):
            """Update map"""
            wellname = Path(wellfile).stem
            wellfile = get_path(wellfile)
            surface = load_surface(str(get_path(self.surfacefiles[0])))
            well = load_well(str(wellfile))
            s_layer = make_surface_layer(
                surface, name=self.surfacenames[0], hillshading=True,
            )
            well_layer = make_well_layer(well, wellname)
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
