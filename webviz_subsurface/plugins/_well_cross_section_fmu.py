from uuid import uuid4
from pathlib import Path
from typing import List
import io
import json

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
from .._datainput.well import load_well
from .._datainput.surface import make_surface_layer

# pylint: disable=too-many-instance-attributes
class WellCrossSectionFMU(WebvizPluginABC):
    """### WellCrossSectionFMU
Well cross-section displaying statistical surfaces from a FMU ensemble.

Statistical surfaces are calculated automatically from surfaces stored
per realization.

* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `surfacefiles`: Surface file names (without folder)
* `surfacenames`: Corresponding list of displayed surface names
* `surfacefolder`: Realization relative folder containing the surface files
* `surfacenames`: Surface names for visualization
* `wellfiles`: List of file paths to RMS wells
* `wellfolder`: Alternatively provide a folder with RMS wells
* `wellsuffix`: File suffix for wells in well folder.
* `segyfiles`: List of file paths to segyfiles
* `zunit`: z-unit for display
* `zonelog`: Name of zonelog in wellfiles (displayed along well trajectory)
* `marginal_logs`: Logs to be displayed in separate horizontal plot
* `zmin`: Visualized minimum z-value in cross section
* `zmax`: Visualized maximum z-value in cross section
* `zonemin`: First zonenumber to draw in log
* `sampling`: Horizontal sampling interval
* `nextend`: Horizontal extension beyond well path (0 is no extension)
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
        marginal_logs: list = None,
        zunit="depth (m)",
        zmin: float = None,
        zmax: float = None,
        zonemin: int = 1,
        nextend: int = 2,
        sampling: int = 40,
        colors: list = None,
    ):

        super().__init__()

        if wellfiles is not None == wellfolder is not None:
            raise ValueError(
                'Incorrent arguments. Either provide "wellfiles" or "wellfolder"'
            )
        self.wellfolder = wellfolder
        self.wellsuffix = wellsuffix
        self.wellfiles = (
            json.load(find_files(wellfolder, wellsuffix))
            if wellfolder is not None
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
        self.marginal_logs = marginal_logs
        self.zunit = zunit
        self.sampling = sampling
        self.nextend = nextend
        self.zmin = zmin
        self.zmax = zmax
        self.zonemin = zonemin
        self.segyfiles = [] if segyfiles is None else [str(segy) for segy in segyfiles]
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
        self.colors = self.plotly_theme["layout"]["colorway"]
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
            style=self.set_style(marginTop="20px"),
            children=html.Label(
                children=[
                    html.Span("Surface:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("surfacenames"),
                        options=[
                            {"label": name, "value": name} for name in self.surfacenames
                        ],
                        value=self.surfacenames,
                        clearable=True,
                        multi=True,
                    ),
                ]
            ),
        )

    @property
    def ensemble_layout(self):
        return html.Div(
            style=self.set_style(marginTop="20px"),
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
            ),
        )

    @property
    def seismic_layout(self):
        if self.segyfiles:
            return html.Div(
                style=self.set_style(marginTop="20px")
                if self.segyfiles
                else {"display": "none"},
                children=html.Label(
                    children=[
                        html.Span("Seismic:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.ids("cube"),
                            options=[
                                {"label": Path(segy).stem, "value": segy}
                                for segy in self.segyfiles
                            ],
                            value=self.segyfiles[0],
                            clearable=False,
                        ),
                    ]
                ),
            )
        return html.Div(id=self.ids("cube"))

    @property
    def marginal_log_layout(self):
        if self.marginal_logs is not None:
            return html.Div(
                children=html.Label(
                    children=[
                        html.Span("Marginal log:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.ids("marginal-log"),
                            options=[
                                {"label": log, "value": log}
                                for log in self.marginal_logs
                            ],
                            placeholder="Display log",
                            clearable=True,
                        ),
                    ]
                ),
            )
        return html.Div(id=self.ids("marginal-log"))

    @property
    def intersection_option(self):
        options = [
            {"label": "Keep zoom state", "value": "keep_zoom_state"},
            {"label": "Show surface fill", "value": "show_surface_fill"},
        ]
        value = ["show_surface_fill"]
        if self.segyfiles:
            options.append({"label": "Show seismic", "value": "show_seismic"})
        if self.zonelog is not None:
            options.append({"label": "Show zonelog", "value": "show_zonelog"})
            value.append("show_zonelog")

        return html.Div(
            style=self.set_style(marginTop="20px"),
            children=[
                html.Label("Intersection settings", style={"font-weight": "bold"}),
                html.Div(
                    style=self.set_grid_layout("1fr 1fr"),
                    children=[
                        html.Label("Sampling"),
                        html.Label("Extension"),
                        dcc.Input(
                            id=self.ids("sampling"),
                            debounce=True,
                            type="number",
                            value=self.sampling,
                        ),
                        dcc.Input(
                            id=self.ids("nextend"),
                            debounce=True,
                            type="number",
                            value=self.nextend,
                        ),
                    ],
                ),
                dcc.Checklist(id=self.ids("options"), options=options, value=value),
            ],
        )

    @property
    def map_layout(self):
        return html.Div(
            style=self.set_style(columns="2fr 1fr"),
            children=[
                dcc.Dropdown(
                    id=self.ids("surface-name"),
                    options=[
                        {"label": name, "value": name} for name in self.surfacenames
                    ],
                    value=self.surfacenames[0],
                    clearable=False,
                    multi=False,
                ),
                dcc.Dropdown(
                    id=self.ids("surface-type"),
                    options=[
                        {"label": name, "value": name}
                        for name in [
                            "stddev",
                            "mean",
                            "p10",
                            "p90",
                            "minimum",
                            "maximum",
                        ]
                    ],
                    value="stddev",
                    clearable=False,
                    multi=False,
                ),
            ],
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_style(columns="1fr 8fr"),
            children=[
                html.Div(
                    children=[
                        self.well_layout,
                        self.surface_names_layout,
                        self.seismic_layout,
                        self.ensemble_layout,
                        self.marginal_log_layout,
                        self.intersection_option,
                    ],
                ),
                html.Div(
                    id=self.ids("viz_wrapper"),
                    style={"position": "relative"},
                    children=[
                        html.Div(wcc.Graph(id=self.ids("graph"))),
                        html.Div(
                            id=self.ids("map_wrapper"),
                            style={
                                "position": "absolute",
                                "width": "30%",
                                "height": "40%",
                                "right": 100,
                                "top": 350,
                                "zIndex": 10000,
                                "visibility": "hidden",
                            },
                            children=[
                                self.map_layout,
                                LayeredMap(height=400, id=self.ids("map"), layers=[]),
                            ],
                        ),
                        html.Button(
                            style={"float": "right"},
                            id=self.ids("show_map"),
                            children="Show map",
                        ),
                        dcc.Store(id=self.ids("fencespec"), data=[]),
                    ],
                ),
            ],
        )

    @staticmethod
    def set_style(columns=None, **kwargs):
        if columns is not None:
            return {
                "display": "grid",
                "alignContent": "space-around",
                "justifyContent": "space-between",
                "gridTemplateColumns": f"{columns}",
                **kwargs,
            }
        return {**kwargs}

    @staticmethod
    def set_grid_layout(columns, **kwargs):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
            **kwargs,
        }

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("graph"), "figure"),
                Output(self.ids("fencespec"), "data"),
            ],
            [
                Input(self.ids("surfacenames"), "value"),
                Input(self.ids("ensembles"), "value"),
                Input(self.ids("wells"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("options"), "value"),
                Input(self.ids("sampling"), "value"),
                Input(self.ids("nextend"), "value"),
                Input(self.ids("marginal-log"), "value"),
            ],
        )
        def _render_section(
            surfacenames, ensemble, well, cube, options, sampling, nextend, marginal_log
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
                show_marginal=marginal_log is not None,
                zunit=self.zunit,
            )

            for surfacename, surfacefile in zip(surfacenames, surfacefiles):
                stat_surfs = get_surface_statistics(
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
                marginal_log=marginal_log,
            )
            layout = xsect.layout
            layout.update(self.plotly_theme["layout"])
            if "keep_zoom_state" in options:
                layout["uirevision"] = "keep"
            fencespec = [[coord[0], coord[1]] for coord in xsect.fence]
            return {"data": xsect.data, "layout": layout}, fencespec

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

            if not nclicks:
                raise PreventUpdate
            if nclicks % 2:
                style["visibility"] = "visible"
                return style, "Hide Map"
            style["visibility"] = "hidden"
            return style, "Show map"

        @app.callback(
            [Output(self.ids("map"), "layers"), Output(self.ids("map"), "uirevision")],
            [
                Input(self.ids("fencespec"), "data"),
                Input(self.ids("surface-name"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("ensembles"), "value"),
            ],
        )
        def _render_surface(fencespec, surfacename, surfacetype, ensemble):
            """Update map"""
            intersect_layer = {
                "name": "Well",
                "checked": True,
                "base_layer": False,
                "data": [{"type": "polyline", "color": "red", "positions": fencespec,}],
            }

            surface = get_surface_statistics(
                self.realizations,
                ensemble,
                self.surfacefiles[self.surfacenames.index(surfacename)],
                self.surfacefolder,
            )[surfacetype]

            surface_layer = make_surface_layer(
                surface, name=surfacename, hillshading=True
            )
            return [surface_layer, intersect_layer], "keep"

    def add_webvizstore(self):
        store_functions = [
            (get_path, [{"path": fn}]) for fn in self.segyfiles + self.wellfiles
        ]
        for ens in list(self.realizations["ENSEMBLE"].unique()):
            for surfacefile in self.surfacefiles:
                store_functions.append(
                    (
                        calculate_surface_statistics,
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

        store_functions.append(
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
        if self.wellfolder is not None:
            store_functions.append(
                (find_files, [{"folder": self.wellfolder, "suffix": self.wellsuffix}])
            )
        return store_functions


@webvizstore
def calculate_surface_statistics(
    realdf, ensemble, surfacefile, surfacefolder
) -> io.BytesIO:
    real_paths = list(realdf[realdf["ENSEMBLE"] == ensemble]["RUNPATH"])
    fns = [
        str(Path(Path(real_path) / Path(surfacefolder) / Path(surfacefile)))
        for real_path in real_paths
    ]
    surfaces = get_surfaces(fns)
    return io.BytesIO(
        json.dumps(
            {
                "mean": surface_to_json(surfaces.apply(np.nanmean, axis=0)),
                "maximum": surface_to_json(surfaces.apply(np.nanmax, axis=0)),
                "minimum": surface_to_json(surfaces.apply(np.nanmin, axis=0)),
                "p10": surface_to_json(surfaces.apply(np.nanpercentile, 10, axis=0)),
                "p90": surface_to_json(surfaces.apply(np.nanpercentile, 90, axis=0)),
                "stddev": surface_to_json(surfaces.apply(np.nanstd, axis=0)),
            }
        ).encode()
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_statistics(realdf, ensemble, surfacefile, surfacefolder):
    surfaces = json.load(
        calculate_surface_statistics(realdf, ensemble, surfacefile, surfacefolder)
    )
    return {
        statistic: surface_from_json(surface) for statistic, surface in surfaces.items()
    }


def surface_to_json(surface):
    return json.dumps(
        {
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xori": surface.xori,
            "yori": surface.yori,
            "rotation": surface.rotation,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
            "values": surface.values.copy().filled(np.nan).tolist(),
        }
    )


def surface_from_json(surfaceobj):
    return xtgeo.RegularSurface(**json.loads(surfaceobj))


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    return xtgeo.surface.surfaces.Surfaces(fns)


@webvizstore
def get_path(path) -> Path:
    return Path(path)


@webvizstore
def find_files(folder, suffix) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )
