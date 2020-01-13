from uuid import uuid4
from pathlib import Path
from typing import List
import io

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
from .._datainput.surface import load_surface, make_surface_layer, get_surface_arr


class WellCrossSectionFMU(WebvizPluginABC):
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
        ensembles,
        surfacefiles: List[Path],
        surfaceattributes: List = None,
        wellfiles: List[Path] = None,
        segyfiles: List[Path] = None,
        surfacenames: list = None,
        surfacenames_visual: List = None,
        zonelog: str = None,
        zunit="depth (m)",
        zmin: float = None,
        zmax: float = None,
        zonemin: int = 1,
        nextend: int = 2,
        sampling: int = 40,
    ):

        super().__init__()

        self.ensembles = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }
        # print(find_files(self.ensembles, 'share/results/maps', '*.gri'))
        self.realizations = get_realizations(
            ensemble_paths=self.ensembles, ensemble_set_name="EnsembleSet"
        )
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
        self.surfacenames_visual = (
            surfacenames_visual if surfacenames_visual else surfacenames
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
    def surface_names_layout(self):
        return html.Div(
            children=html.Label(
                children=[
                    html.Span("Well:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("surfacenames"),
                        options=[
                            {"label": visname, "value": name}
                            for visname, name in zip(
                                self.surfacenames_visual, self.surfacenames
                            )
                        ],
                        value=self.surfacenames[0],
                        clearable=False,
                        multi=True,
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
                        self.surface_names_layout,
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
                Input(self.ids("surfacenames"), "value"),
                Input(self.ids("wells"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("options"), "value"),
                Input(self.ids("sampling"), "value"),
                Input(self.ids("nextend"), "value"),
            ],
        )
        def _render_section(surfacenames, well, cube, options, sampling, nextend):
            """Update cross section"""

            well = load_well(str(get_path(well)))
            xsect = XSectionFigure(
                well=well,
                zmin=self.zmin,
                zmax=self.zmax,
                nextend=int(nextend),
                sampling=int(sampling),
            )
            surfacenames = (
                surfacenames if isinstance(surfacenames, list) else [surfacenames]
            )

            colors = [
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
            for i, surfacename in enumerate(surfacenames):
                stat = calculate_surface_statistics(
                    self.realizations, "iter-0", surfacename, "ds_extracted_horizons"
                )
                xsect.plot_statistical_surface(stat, color=colors[i])

            if "show_seismic" in options:
                cube = load_cube_data(str(get_path(cube)))
                xsect.plot_cube(cube)

            xsect.plot_well(
                zonelogname=self.zonelog if "show_zonelog" in options else None,
                zonemin=self.zonemin,
            )
            xsect.layout["margin"] = {"t": 0}
            return {"data": xsect.data, "layout": xsect.layout}

        # @app.callback(
        #     [
        #         Output(self.ids("map_wrapper"), "style"),
        #         Output(self.ids("show_map"), "children"),
        #     ],
        #     [Input(self.ids("show_map"), "n_clicks")],
        #     [State(self.ids("map_wrapper"), "style")],
        # )
        # def _show_map(nclicks, style):
        #     """Show/hide map on button click"""
        #     btn = "Show Map"
        #     if not nclicks:
        #         raise PreventUpdate
        #     if nclicks % 2:
        #         style["visibility"] = "visible"
        #         btn = "Hide Map"
        #     else:
        #         style["visibility"] = "hidden"
        #     return style, btn

        # @app.callback(
        #     [Output(self.ids("map"), "layers"), Output(self.ids("map"), "uirevision")],
        #     [Input(self.ids("wells"), "value")],
        # )
        # def _render_surface(wellfile):
        #     """Update map"""
        #     wellname = Path(wellfile).stem
        #     wellfile = get_path(wellfile)
        #     surface = load_surface(str(get_path(self.surfacefiles[0])))
        #     well = load_well(str(wellfile))
        #     s_layer = make_surface_layer(
        #         surface, name=self.surfacenames[0], hillshading=True,
        #     )
        #     well_layer = make_well_layer(well, wellname)
        #     return [s_layer, well_layer], "keep"

    def add_webvizstore(self):
        stat_functions = []
        for reals, reals_df in self.realizations.groupby("ENSEMBLE"):
            for surfacename in [
                "topupperreek",
                "topmidreek",
                "toplowerreek",
                "baselowerreek",
            ]:
                for surfaceattr in ["ds_extracted_horizons"]:
                    fns = [
                        make_fmu_file_path(real, surfacename, surfaceattr)
                        for real in list(reals_df["RUNPATH"])
                    ]
                    for stat in ["mean", "maximum", "minimum", "p10", "p90"]:
                        stat_functions.append(
                            (
                                get_surface_statistic,
                                [
                                    {
                                        "fns": fns,
                                        "statistic": stat,
                                        "ensemble": "iter-0",
                                        "surfacename": surfacename,
                                        "surfaceattr": "ds_extracted_horizons",
                                    }
                                ],
                            ))
        for fn in self.segyfiles:
            stat_functions.append((get_path, [{"path": fn}]))
        for fn in self.wellfiles:
            stat_functions.append((get_path, [{"path": fn}]))
                        
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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    import xtgeo

    return xtgeo.surface.surfaces.Surfaces(fns)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def get_surface_statistic(
    fns, statistic, ensemble, surfacename, surfaceattr
) -> io.BytesIO:
    import io, pickle
    import xtgeo
    import numpy as np

    surfaces = get_surfaces(fns)
    if statistic == "mean":
        surface = surfaces.apply(np.nanmean, axis=0)
    if statistic == "maximum":
        surface = surfaces.apply(np.nanmax, axis=0)
    if statistic == "minimum":
        surface = surfaces.apply(np.nanmin, axis=0)
    if statistic == "p10":
        surface = surfaces.apply(np.nanpercentile, 10, axis=0)
    if statistic == "p90":
        surface = surfaces.apply(np.nanpercentile, 90, axis=0)
    return io.BytesIO(pickle.dumps(surface))
    return surface


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface_statistics(realdf, ensemble, surfacename, surfaceattr):
    import xtgeo
    import numpy as np
    import pandas as pd
    import pickle

    real_paths = list(realdf[realdf["ENSEMBLE"] == ensemble]["RUNPATH"])
    fns = [make_fmu_file_path(real, surfacename, surfaceattr) for real in real_paths]
    print(fns)
    return {
        "mean": pickle.loads(
            get_surface_statistic(
                fns, "mean", ensemble, surfacename, surfaceattr
            ).read()
        ),
        "maximum": pickle.loads(
            get_surface_statistic(
                fns, "maximum", ensemble, surfacename, surfaceattr
            ).read()
        ),
        "minimum": pickle.loads(
            get_surface_statistic(
                fns, "minimum", ensemble, surfacename, surfaceattr
            ).read()
        ),
        "p10": pickle.loads(
            get_surface_statistic(fns, "p10", ensemble, surfacename, surfaceattr).read()
        ),
        "p90": pickle.loads(
            get_surface_statistic(fns, "p90", ensemble, surfacename, surfaceattr).read()
        ),
    }


def make_fmu_file_path(
    basepath: Path,
    name,
    attr,
    folder: Path = "share/results/maps",
    suffix=".gri",
    sep="--",
):
    filename = Path(name + sep + attr + suffix)
    return str(Path(basepath / Path(folder) / filename))


@webvizstore
def get_path(path) -> Path:
    return Path(path)
