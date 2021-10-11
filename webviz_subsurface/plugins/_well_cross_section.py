from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union
from uuid import uuid4

import webviz_core_components as wcc
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC
from webviz_config.deprecation_decorators import deprecated_plugin
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._models import SurfaceLeafletModel

from .._datainput.seismic import load_cube_data
from .._datainput.surface import load_surface
from .._datainput.well import load_well, make_well_layer
from .._datainput.xsection import XSectionFigure


@deprecated_plugin(
    "Relevant functionality is implemented in the StructuralUncertainty plugin."
)
class WellCrossSection(WebvizPluginABC):
    """Displays a cross section along a well with intersected surfaces,
and optionally seismic cubes.

!> See also WellCrossSectionFMU for additional functionality with FMU ensembles.
---

* **`segyfiles`:** List of file paths to segyfiles (absolute or relative to config file).
* **`surfacefiles`:** List of file paths to Irap binary surfaces \
(absolute or relative to config file).
* **`surfacenames`:** Corresponding list of displayed surface names.
* **`wellfiles`:** List of file paths to RMS wells (absolute or relative to config file).
* **`zunit`:** z-unit for display.
* **`zonelog`:** Name of zonelog (for the RMS wells in `wellfiles`).
* **`zmin`:** Visualized minimum z-value in cross section.
* **`zmax`:** Visualized maximum z-value in cross section.
* **`zonemin`:** First zonenumber to draw in log.
* **`sampling`:** Sampling interval of well fence.
* **`nextend`:** Number of samples to extend well fence on each side of well, \
e.g. with distance of sampling=20 and nextend=2: extension=2*20 (nextend*sampling). \

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

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        surfacefiles: List[Path],
        wellfiles: List[Path],
        segyfiles: List[Path] = None,
        surfacenames: list = None,
        zonelog: str = None,
        zunit: str = "depth (m)",
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
        self.surfacefiles = [str(surface) for surface in surfacefiles]
        self.wellfiles = [str(well) for well in wellfiles]
        self.segyfiles = [str(segy) for segy in segyfiles] if segyfiles else []
        self.surfacenames: List[str] = (
            surfacenames if surfacenames else [surface.stem for surface in surfacefiles]
        )
        self.zonelog = zonelog
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
            ),
        )

    @property
    def seismic_layout(self) -> html.Div:
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
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def viz_options_layout(self) -> dcc.Checklist:
        options = [{"label": "Show surface fill", "value": "show_surface_fill"}]
        value = ["show_surface_fill"]
        if self.segyfiles:
            options.append({"label": "Show seismic", "value": "show_seismic"})
        if self.zonelog:
            options.append({"label": "Show zonelog", "value": "show_zonelog"})
            value.append("show_zonelog")

        return dcc.Checklist(
            id=self.ids("options"),
            options=options,
            value=value,
            persistence=True,
            persistence_type="session",
        )

    @property
    def well_options(self) -> html.Div:
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
                                required=True,
                                value=self.sampling,
                                persistence=True,
                                persistence_type="session",
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
                                required=True,
                                value=self.nextend,
                                persistence=True,
                                persistence_type="session",
                            ),
                        ]
                    )
                ),
            ],
        )

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 1fr 1fr 1fr 1fr"),
                    children=[
                        self.well_layout,
                        self.well_options,
                        self.seismic_layout,
                        self.viz_options_layout,
                        html.Button(
                            id=self.ids("show_map"),
                            children="Show map",
                        ),
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
                            children=LeafletMap(
                                id=self.ids("map"),
                                layers=[],
                                unitScale={},
                                autoScaleMap=True,
                                minZoom=-19,
                                updateMode="update",
                                mouseCoords={"position": "bottomright"},
                                colorBar={"position": "bottomleft"},
                            ),
                        ),
                        wcc.Graph(id=self.ids("graph")),
                    ],
                ),
            ],
        )

    @staticmethod
    def set_grid_layout(columns: str) -> Dict[str, str]:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def set_callbacks(self, app: Dash) -> None:
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
        def _render_section(
            wellfile: str,
            cubefile: str,
            options: List[str],
            sampling: Union[int, float, None],
            nextend: Union[int, float, None],
        ) -> dict:
            """Update cross section"""

            if sampling is None or nextend is None:
                raise PreventUpdate

            well = load_well(get_path(wellfile))
            xsect = XSectionFigure(
                well=well,
                zmin=self.zmin,
                zmax=self.zmax,
                nextend=int(nextend),
                sampling=int(sampling),
            )

            surfaces = [load_surface(get_path(surf)) for surf in self.surfacefiles]

            xsect.plot_surfaces(
                surfaces=surfaces,
                surfacenames=self.surfacenames,
                fill="show_surface_fill" in options,
            )

            if "show_seismic" in options:
                cube = load_cube_data(get_path(cubefile))
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
        def _show_map(nclicks: int, style: dict) -> Tuple[dict, str]:
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
            Output(self.ids("map"), "layers"),
            [Input(self.ids("wells"), "value")],
        )
        def _render_surface(wellfile: str) -> List[Dict[str, Any]]:
            """Update map"""
            wellname = Path(wellfile).stem
            wellfile = get_path(wellfile)
            surface = load_surface(get_path(self.surfacefiles[0]))
            well = load_well(wellfile)
            s_layer = SurfaceLeafletModel(surface, name=self.surfacenames[0]).layer
            well_layer = make_well_layer(well, wellname)
            return [s_layer, well_layer]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            *[(get_path, [{"path": fn}]) for fn in self.segyfiles],
            *[(get_path, [{"path": fn}]) for fn in self.surfacefiles],
            *[(get_path, [{"path": fn}]) for fn in self.wellfiles],
        ]


@webvizstore
def get_path(path: str) -> Path:
    return Path(path)
