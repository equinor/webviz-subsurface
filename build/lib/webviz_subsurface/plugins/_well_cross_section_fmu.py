import io
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
import xtgeo
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.deprecation_decorators import deprecated_plugin
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._models import SurfaceLeafletModel

from .._datainput.fmu_input import get_realizations
from .._datainput.seismic import load_cube_data
from .._datainput.well import load_well
from .._datainput.xsection import XSectionFigure


# pylint: disable=too-many-instance-attributes
@deprecated_plugin(
    "Relevant functionality is implemented in the StructuralUncertainty plugin."
)
class WellCrossSectionFMU(WebvizPluginABC):
    """Well cross-section displaying statistical surfaces from a FMU ensemble.

Statistical surfaces are calculated automatically from surfaces stored
per realization.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`surfacefiles`:** Surface file names (without folder).
* **`surfacenames`:** List corresponding to `surfacefiles` of displayed surface names.
* **`surfacefolder`:** Realization relative folder containing the `surfacefiles`.
* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).
* **`wellfolder`:** Alternative to `wellfiles`: provide a folder with RMS wells. \
(absolute or relative to config file).
* **`wellsuffix`:** File suffix for wells in `wellfolder`.
* **`segyfiles`:** List of file paths to `segyfiles` (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`zonelog`:** Name of zonelog in `wellfiles` (displayed along well trajectory).
* **`marginal_logs`:** Logs in `wellfiles` to be displayed in separate horizontal plot.
* **`zmin`:** Visualized minimum z-value in cross section.
* **`zmax`:** Visualized maximum z-value in cross section.
* **`zonemin`:** First zonenumber to draw in zone log.
* **`sampling`:** Horizontal sampling interval.
* **`nextend`:** Number of samples to extend well fence on each side of well, \
e.g. `sampling=20` and `nextend=2` results in `extension=20*2`. \
* **`colors`:** List of hex colors corresponding to surfaces. Note that apostrophies \
    should be used to avoid that hex colors are read as comments. E.g. `'#000000'` for black.

---

**Example files**

* [Segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
observed_data/seismic).

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/\
maps/topupperreek--ds_extracted_horizons.gri).

* [Wellfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
observed_data/wells).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

The surfacefiles are on a `ROFF binary` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).
"""

    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        surfacefiles: list,
        surfacenames: list = None,
        surfacefolder: Path = Path("share/results/maps"),
        wellfiles: List[Path] = None,
        wellfolder: Path = None,
        wellsuffix: str = ".w",
        segyfiles: List[Path] = None,
        zonelog: str = None,
        marginal_logs: list = None,
        zunit: str = "depth (m)",
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
        self.wellfiles: List[str]
        if wellfolder is not None:
            self.wellfiles = json.load(find_files(wellfolder, wellsuffix))
        elif wellfiles is not None:
            self.wellfiles = [str(well) for well in wellfiles]

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
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.realizations: pd.DataFrame = get_realizations(
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
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.colors = (
            colors
            if colors is not None
            else self.plotly_theme.get("layout", {}).get(
                "colorway",
                [
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
                ],
            )
        )

        self.uid = uuid4()
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def well_layout(self) -> html.Div:
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
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            )
        )

    @property
    def surface_names_layout(self) -> html.Div:
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
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def ensemble_layout(self) -> html.Div:
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
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def seismic_layout(self) -> html.Div:
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
                            persistence=True,
                            persistence_type="session",
                        ),
                    ]
                ),
            )
        return html.Div(
            style={"visibility": "hidden"}, children=dcc.Dropdown(id=self.ids("cube"))
        )

    @property
    def marginal_log_layout(self) -> html.Div:
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
                            persistence=True,
                            persistence_type="session",
                        ),
                    ]
                ),
            )
        return html.Div(
            style={"visibility": "hidden"},
            children=dcc.Dropdown(id=self.ids("marginal-log"), persistence=True),
        )

    @property
    def intersection_option(self) -> html.Div:
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
                html.Label("Sampling"),
                dcc.Input(
                    id=self.ids("sampling"),
                    debounce=True,
                    type="number",
                    required=True,
                    value=self.sampling,
                    persistence=True,
                    persistence_type="session",
                ),
                html.Label("Extension"),
                dcc.Input(
                    id=self.ids("nextend"),
                    debounce=True,
                    type="number",
                    required=True,
                    value=self.nextend,
                    persistence=True,
                    persistence_type="session",
                ),
                dcc.Checklist(
                    id=self.ids("options"),
                    options=options,
                    value=value,
                    persistence=True,
                    persistence_type="session",
                ),
            ],
        )

    @property
    def map_layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                dcc.Dropdown(
                    id=self.ids("surface-name"),
                    options=[
                        {"label": name, "value": name} for name in self.surfacenames
                    ],
                    value=self.surfacenames[0],
                    clearable=False,
                    multi=False,
                    persistence=True,
                    persistence_type="session",
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
                    persistence=True,
                    persistence_type="session",
                ),
            ],
        )

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            children=[
                html.Div(
                    style={"flex": 1},
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
                    style={"position": "relative", "flex": 8},
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
                                LeafletMap(
                                    id=self.ids("map"),
                                    layers=[],
                                    unitScale={},
                                    autoScaleMap=True,
                                    minZoom=-5,
                                    updateMode="update",
                                    mouseCoords={"position": "bottomright"},
                                    colorBar={"position": "bottomleft"},
                                ),
                            ],
                        ),
                        html.Button(
                            style={"float": "right"},
                            id=self.ids("show_map"),
                            children="Show map",
                        ),
                        dcc.Store(
                            id=self.ids("fencespec"), storage_type="session", data=[]
                        ),
                    ],
                ),
            ],
        )

    @staticmethod
    def set_style(columns: str = None, **kwargs: Any) -> dict:
        if columns is not None:
            return {
                "display": "grid",
                "alignContent": "space-around",
                "justifyContent": "space-between",
                "gridTemplateColumns": f"{columns}",
                **kwargs,
            }
        return {**kwargs}

    def set_callbacks(self, app: Dash) -> None:
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
            surfacenames: List[str],
            ensemble: str,
            wellfile: str,
            segyfile: str,
            options: List[str],
            sampling: Union[int, float, None],
            nextend: Union[int, float, None],
            marginal_log: Union[str, None],
        ) -> Tuple[dict, List[List[float]]]:
            """Update cross section"""

            # TODO(Sigurd) According to dcc.Dropdown doc, surfacename should always be of
            # type List[str] since multi=True
            if not isinstance(surfacenames, list):
                raise TypeError("surfacenames must be of type list")

            # TODO(Sigurd) Can we prohibit clearing of the sampling and nextend input
            # fields (dcc.Input) in the client? Until we can, we must guard against sampling
            # and nextend being None. This happens when the user clears the input field and we
            # have not yet found a solution that prohibits the input field from being cleared.
            # The situation can be slightly remedied by setting required=True which will highlight
            # the missing value with a red rectangle.
            if sampling is None or nextend is None:
                raise PreventUpdate

            # Sort selected surfaces
            surfacenames = [name for name in self.surfacenames if name in surfacenames]
            surfacefiles = [
                self.surfacefiles[self.surfacenames.index(name)]
                for name in surfacenames
            ]
            well = load_well(get_path(wellfile))
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
                    self.realizations.to_dict(orient="records"),
                    ensemble,
                    surfacefile,
                    self.surfacefolder,
                )
                xsect.plot_statistical_surface(
                    stat_surfs, name=surfacename, fill="show_surface_fill" in options
                )

            if "show_seismic" in options:
                cube = load_cube_data(get_path(segyfile))
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
            # [[]] "solves" type hint, but is pretty dirty
            # and probably wrong...
            fencespec: List[List[float]] = []
            if xsect.fence is not None:
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
        def _show_map(nclicks: int, style: dict) -> Tuple[dict, str]:
            """Show/hide map on button click"""

            if not nclicks:
                raise PreventUpdate
            if nclicks % 2:
                style["visibility"] = "visible"
                return style, "Hide Map"
            style["visibility"] = "hidden"
            return style, "Show map"

        @app.callback(
            Output(self.ids("map"), "layers"),
            [
                Input(self.ids("fencespec"), "data"),
                Input(self.ids("surface-name"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("ensembles"), "value"),
            ],
        )
        def _render_surface(
            fencespec: List[List[float]],
            surfacename: str,
            surfacetype: str,
            ensemble: str,
        ) -> List[dict]:
            """Update map"""
            intersect_layer = {
                "name": "Well",
                "id": "Well",
                "action": "replace",
                "checked": True,
                "base_layer": False,
                "data": [
                    {
                        "type": "polyline",
                        "color": "red",
                        "positions": fencespec,
                    }
                ],
            }

            surface = get_surface_statistics(
                self.realizations.to_dict(orient="records"),
                ensemble,
                self.surfacefiles[self.surfacenames.index(surfacename)],
                self.surfacefolder,
            )[surfacetype]

            surface_layer = SurfaceLeafletModel(surface, name=surfacename).layer
            return [surface_layer, intersect_layer]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions: List[Tuple[Callable, list]] = [
            (get_path, [{"path": fn}]) for fn in self.segyfiles + self.wellfiles
        ]

        for ens in list(self.realizations["ENSEMBLE"].unique()):
            for surfacefile in self.surfacefiles:
                store_functions.append(
                    (
                        calculate_surface_statistics,
                        [
                            {
                                "realdf_dict": self.realizations.to_dict(
                                    orient="records"
                                ),
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
    realdf_dict: list, ensemble: str, surfacefile: str, surfacefolder: Path
) -> io.BytesIO:

    realdf = pd.DataFrame(realdf_dict)

    fns = [
        os.path.join(real_path, surfacefolder, surfacefile)
        for real_path in list(realdf[realdf["ENSEMBLE"] == ensemble]["RUNPATH"])
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
def get_surface_statistics(
    realdf_dict: list, ensemble: str, surfacefile: str, surfacefolder: Path
) -> Dict[str, xtgeo.RegularSurface]:
    surfaces = json.load(
        calculate_surface_statistics(realdf_dict, ensemble, surfacefile, surfacefolder)
    )
    return {
        statistic: surface_from_json(surface) for statistic, surface in surfaces.items()
    }


def surface_to_json(surface: xtgeo.RegularSurface) -> str:
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


def surface_from_json(surfaceobj: Union[str, bytes]) -> xtgeo.RegularSurface:
    # See https://github.com/equinor/xtgeo/issues/405
    data = json.loads(surfaceobj)
    surface = xtgeo.RegularSurface(**data)
    surface.values = np.array(data["values"])
    return surface


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns: List[str]) -> xtgeo.Surfaces:
    return xtgeo.Surfaces(fns)


@webvizstore
def get_path(path: str) -> Path:
    return Path(path)


@webvizstore
def find_files(folder: Path, suffix: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            sorted([str(filename) for filename in folder.glob(f"*{suffix}")])
        ).encode()
    )
