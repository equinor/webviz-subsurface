from uuid import uuid4
from pathlib import Path
from typing import List
import io
import glob
import pickle

import numpy as np

import xtgeo
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from .._datainput.fmu_input import get_realizations
from .._datainput.xsection import XSectionFigure
from .._datainput.seismic import load_cube_data
from .._datainput.well import load_well, make_well_layer
from .._datainput.surface import make_surface_layer


class WellCrossSectionFMU(WebvizPluginABC):
    """### WellCrossSection
    Displays a cross section along a well with intersected statistical surfaces,
    from an FMU ensemble and optionally seismic cubes.

    Statistical surfaces are calculated automatically from surfaces stored
    per realization.

* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `surfacefiles`: Surface file names (without folder)
* `surfacenames`: Corresponding list of displayed surface names
* `surfacefolder`: The surface folder
* `surfacenames`: Surface names for visualization
* `wellfiles`: List of file paths to RMS wells
* `wellfolder`: Alternatively provide a folder with RMS wells
* `wellsuffix`: File suffix for wells in well folder.
* `segyfiles`: List of file paths to segyfiles
* `zunit`: z-unit for display
* `zonelog`: Name of zonelog
* `zmin`: Visualized minimum z-value in cross section
* `zmax`: Visualized maximum z-value in cross section
* `zonemin`: First zonenumber to draw in log
* `sampling`: Sampling interval of well fence
* `nextend`: Number to extend distance of sampling, e.g. 2*20 (nextend*sampling)
* `colors`: List of colors corresponding to surfaces

"""

    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        app,
        ensembles,
        surfacefiles: list,
        surfacenames: list = None,
        surfacefolder: Path = "share/results/maps",
        wellfiles: List[Path] = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        segyfiles: List[Path] = None,
        zonelog: str = None,
        zunit="depth (m)",
        zmin: float = None,
        zmax: float = None,
        zonemin: int = 1,
        nextend: int = 2,
        sampling: int = 40,
        colors: list = None,
    ):

        super().__init__()

        if wellfiles and wellfolder:
            raise ValueError(
                'Incorrent arguments. Either provide "wellfiles" or "wellfolder"'
            )
        if not wellfiles and not wellfolder:
            raise ValueError(
                'Incorrent arguments. Either provide "wellfiles" or "wellfolder"'
            )
        self.wellfiles = (
            glob.glob(str(wellfolder / wellsuffix))
            if wellfolder
            else [str(well) for well in wellfiles]
        )

        self.surfacefolder = surfacefolder
        self.surfacefiles = surfacefiles

        if surfacenames:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = surfacefiles

        self.ensembles = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.realizations = get_realizations(
            ensemble_paths=self.ensembles, ensemble_set_name="EnsembleSet"
        )

        self.zunit = zunit
        self.sampling = sampling
        self.nextend = nextend
        self.zmin = zmin
        self.zmax = zmax
        self.zonemin = zonemin
        self.segyfiles = [str(segy) for segy in segyfiles] if segyfiles else []

        self.zonelog = zonelog

        self.colors = (
            colors
            if colors
            else [
                "#1f77b4",  # muted blue
                "#ff7f0e",  # safety orange
                "#2ca02c",  # cooked asparagus green
                "#d62728",  # brick red
                "#9467bd",  # muted purple
                "#8c564b",  # chestnut brown
                "#e377c2",  # raspberry yogurt pink
                "#7f7f7f",  # middle gray
                "#bcbd22",  # curry yellow-green
                "#17becf",  # blue-teal
            ]
        )
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
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
            )
        )

    @property
    def surface_names_layout(self):
        return html.Div(
            children=html.Label(
                children=[
                    html.Span("Surface:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("surfacenames"),
                        options=[
                            {"label": name, "value": name} for name in self.surfacenames
                        ],
                        value=self.surfacenames[0],
                        clearable=False,
                        multi=True,
                    ),
                ]
            )
        )

    @property
    def ensemble_layout(self):
        return html.Div(
            children=html.Label(
                children=[
                    html.Span("Ensemble:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("ensembles"),
                        options=[
                            {"label": ens, "value": ens}
                            for ens in self.ensembles.keys()
                        ],
                        value=list(self.ensembles.keys())[0],
                        clearable=False,
                        multi=False,
                    ),
                ]
            )
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

        return dcc.Checklist(id=self.ids("options"), options=options, value=value)

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
    def map_layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 1fr"),
            children=[
                html.Button(id=self.ids("show_map"), children="Show stddev map"),
                dcc.Dropdown(
                    id=self.ids("stddev-surface"),
                    options=[
                        {"label": name, "value": name} for name in self.surfacenames
                    ],
                    value=self.surfacenames[0],
                    clearable=False,
                    multi=False,
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
                        html.Div(self.seismic_layout),
                        self.viz_options_layout,
                        self.map_layout,
                    ],
                ),
                html.Div(
                    style=self.set_grid_layout("1fr 1fr 1fr 1fr 1fr"),
                    children=[self.surface_names_layout, self.ensemble_layout],
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
            ]
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
                Input(self.ids("surfacenames"), "value"),
                Input(self.ids("ensembles"), "value"),
                Input(self.ids("wells"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("options"), "value"),
                Input(self.ids("sampling"), "value"),
                Input(self.ids("nextend"), "value"),
            ],
        )
        def _render_section(
            surfacenames, ensemble, well, cube, options, sampling, nextend
        ):
            """Update cross section"""
            # Ensure list
            surfacenames = (
                surfacenames if isinstance(surfacenames, list) else [surfacenames]
            )
            # Sort selected surfaces
            surfacenames = [name for name in self.surfacenames if name in surfacenames]
            surfacefiles = [
                self.surfacefiles[self.surfacenames.index(name)]
                for name in surfacenames
            ]
            well = load_well(str(get_path(well)))
            xsect = XSectionFigure(
                well=well,
                zmin=self.zmin,
                zmax=self.zmax,
                nextend=int(nextend),
                sampling=int(sampling),
                surfacenames=self.surfacenames,
                surfacecolors=self.colors,
            )

            for surfacename, surfacefile in zip(surfacenames, surfacefiles):
                stat_surfs = calculate_surface_statistics(
                    self.realizations, ensemble, surfacefile, self.surfacefolder
                )
                xsect.plot_statistical_surface(
                    stat_surfs, name=surfacename, fill="show_surface_fill" in options
                )

            if "show_seismic" in options:
                cube = load_cube_data(str(get_path(cube)))
                xsect.plot_cube(cube)

            xsect.plot_well(
                zonelogname=self.zonelog if "show_zonelog" in options else None,
                zonemin=self.zonemin,
            )
            xsect.layout.update(self.plotly_theme["layout"])
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
            btn = "Show Stddev Map"
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
            [
                Input(self.ids("wells"), "value"),
                Input(self.ids("stddev-surface"), "value"),
                Input(self.ids("ensembles"), "value"),
            ],
        )
        def _render_surface(wellfile, surfacename, ensemble):
            """Update map"""
            wellname = Path(wellfile).stem
            wellfile = get_path(wellfile)
            well = load_well(str(wellfile))
            well_layer = make_well_layer(well, wellname)
            surface = calculate_surface_statistics(
                self.realizations,
                ensemble,
                self.surfacefiles[self.surfacenames.index(surfacename)],
                self.surfacefolder,
            )["stddev"]

            surface_layer = make_surface_layer(
                surface, name=surfacename, hillshading=True
            )
            return [surface_layer, well_layer], "keep"

    def add_webvizstore(self):
        stat_functions = []
        for ens in list(self.realizations["ENSEMBLE"].unique()):
            for surfacefile in self.surfacefiles:
                stat_functions.append(
                    (
                        get_surface_statistics,
                        [
                            {
                                "realdf": self.realizations,
                                "ensemble": ens,
                                "surfacefile": surfacefile,
                                "surfacefolder": self.surfacefolder,
                            }
                        ],
                    )
                )
        for filename in self.segyfiles:
            stat_functions.append((get_path, [{"path": filename}]))
        for filename in self.wellfiles:
            stat_functions.append((get_path, [{"path": filename}]))

        stat_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ensembles,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        return stat_functions


@webvizstore
def get_surface_statistics(realdf, ensemble, surfacefile, surfacefolder) -> io.BytesIO:
    real_paths = list(realdf[realdf["ENSEMBLE"] == ensemble]["RUNPATH"])
    fns = [
        str(Path(Path(real_path) / Path(surfacefolder) / Path(surfacefile)))
        for real_path in real_paths
    ]
    surfaces = get_surfaces(fns)

    return io.BytesIO(
        pickle.dumps(
            {
                "mean": surfaces.apply(np.nanmean, axis=0),
                "maximum": surfaces.apply(np.nanmax, axis=0),
                "minimum": surfaces.apply(np.nanmin, axis=0),
                "p10": surfaces.apply(np.nanpercentile, 10, axis=0),
                "p90": surfaces.apply(np.nanpercentile, 90, axis=0),
                "stddev": surfaces.apply(np.nanstd, axis=0),
            }
        )
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface_statistics(realdf, ensemble, surfacefile, surfacefolder):
    return pickle.loads(
        get_surface_statistics(realdf, ensemble, surfacefile, surfacefolder).read()
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    return xtgeo.surface.surfaces.Surfaces(fns)


@webvizstore
def get_path(path) -> Path:
    return Path(path)
