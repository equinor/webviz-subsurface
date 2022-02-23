from pathlib import Path
from typing import List
from uuid import uuid4

import pandas as pd
import webviz_core_components as wcc
import xtgeo
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import LeafletMap

from webviz_subsurface._models import SurfaceLeafletModel

from .._datainput.seismic import load_cube_data
from .._datainput.surface import get_surface_fence


class SurfaceWithSeismicCrossSection(WebvizPluginABC):
    """Visualizes surfaces in a map view and seismic in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.

---

* **`segyfiles`:** List of file paths to SEG-Y files (absolute or relative to config file).
* **`segynames`:** Corresponding list of displayed seismic names.
* **`surfacefiles`:** List of file paths to Irap Binary surfaces \
(absolute or relative to config file).
* **`surfacenames`:** Corresponding list of displayed surface names.
* **`zunit`:** z-unit for display
* **`colors`:** List of hex colors to use. \
Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. \
`'#000000'` for black.

---

**Example files**

* [Segyfiles](https://github.com/equinor/webviz-subsurface-testdata/tree/master/\
observed_data/seismic).

* [One file for surfacefiles](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/\
maps/topupperreek--ds_extracted_horizons.gri).

The segyfiles are on a `SEG-Y` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).

The surfacefiles are on a `ROFF binary` format and can be investigated outside `webviz` using \
e.g. [xtgeo](https://xtgeo.readthedocs.io/en/latest/).
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        segyfiles: List[Path],
        surfacefiles: List[Path],
        surfacenames: list = None,
        segynames: list = None,
        zunit="depth (m)",
        colors: list = None,
    ):

        super().__init__()
        self.zunit = zunit
        self.segyfiles = [str(segyfile) for segyfile in segyfiles]
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]
        if segynames is not None:
            if len(segynames) != len(segyfiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of segyfiles"
                )
            self.segynames = segynames
        else:
            self.segynames = [Path(segyfile).stem for segyfile in segyfiles]
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.initial_colors = (
            colors
            if colors is not None
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
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "Plugin to display surfaces and random lines from a seismic cube. "
                ),
            },
            {
                "id": self.ids("surface"),
                "content": ("The visualized surface."),
            },
            {
                "id": self.ids("map-view"),
                "content": (
                    "Map view of the surface. Use the right toolbar to "
                    "draw a random line."
                ),
            },
            {
                "id": self.ids("fence-view"),
                "content": (
                    "Cross section view of the seismic cube along the edited line. "
                    "The view is empty until a random line is drawn in the map view."
                ),
            },
            {
                "id": self.ids("surface-type"),
                "content": (
                    "Display the z-value of the surface (e.g. depth) or "
                    "the seismic value where the surface intersect the seismic cube."
                ),
            },
            {
                "id": self.ids("cube"),
                "content": "The visualized cube.",
            },
            {
                "id": self.ids("color-scale"),
                "content": ("Click this button to change colorscale"),
            },
            {
                "id": self.ids("color-values"),
                "content": ("Drag either node of slider to truncate color ranges"),
            },
            {
                "id": self.ids("color-range-btn"),
                "content": (
                    "Click this button to update color slider min/max and reset ranges."
                ),
            },
        ]

    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                wcc.Frame(
                    style={"flex": 1},
                    children=[
                        wcc.Selectors(
                            label="Map settings",
                            children=[
                                wcc.Dropdown(
                                    id=self.ids("surface"),
                                    label="Select surface",
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.surfacenames, self.surfacefiles
                                        )
                                    ],
                                    value=self.surfacefiles[0],
                                    clearable=False,
                                ),
                                wcc.RadioItems(
                                    id=self.ids("surface-type"),
                                    options=[
                                        {
                                            "label": "Display surface z-value",
                                            "value": "surface",
                                        },
                                        {
                                            "label": "Display seismic attribute as z-value",
                                            "value": "attribute",
                                        },
                                    ],
                                    value="surface",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Intersection settings",
                            children=[
                                wcc.Dropdown(
                                    label="Select seismic cube",
                                    id=self.ids("cube"),
                                    options=[
                                        {"label": Path(cube).stem, "value": cube}
                                        for cube in self.segyfiles
                                    ],
                                    value=self.segyfiles[0],
                                    clearable=False,
                                ),
                                wcc.Label(
                                    children="Set colorscale",
                                ),
                                wcc.ColorScales(
                                    id=self.ids("color-scale"),
                                    colorscale=self.initial_colors,
                                    nSwatches=12,
                                ),
                                wcc.RangeSlider(
                                    label="Set color range",
                                    id=self.ids("color-values"),
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                    marks=None,
                                ),
                                html.Button(
                                    id=self.ids("color-range-btn"),
                                    children="Reset Range",
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    highlight=False,
                    style={
                        "height": "800px",
                        "flex": 3,
                    },
                    children=[
                        LeafletMap(
                            id=self.ids("map-view"),
                            autoScaleMap=True,
                            minZoom=-19,
                            updateMode="update",
                            layers=[],
                            drawTools={
                                "drawMarker": False,
                                "drawPolygon": False,
                                "drawPolyline": True,
                                "position": "topright",
                            },
                            mouseCoords={"position": "bottomright"},
                            colorBar={"position": "bottomleft"},
                            switch={
                                "value": False,
                                "disabled": False,
                                "label": "Hillshading",
                            },
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 3, "height": "800px"},
                    children=[
                        wcc.Graph(
                            config={"displayModeBar": False}, id=self.ids("fence-view")
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("surface"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("map-view"), "switch"),
            ],
        )
        def _render_surface(
            surfacepath, surface_type, cubepath, color_values, hillshade
        ):

            surface = xtgeo.surface_from_file(get_path(surfacepath))
            min_val = None
            max_val = None
            if surface_type == "attribute":
                min_val = color_values[0] if color_values else None
                max_val = color_values[1] if color_values else None
                cube = load_cube_data(get_path(cubepath))
                surface.slice_cube(cube)
            return [
                SurfaceLeafletModel(
                    surface,
                    name="surface",
                    clip_min=min_val,
                    clip_max=max_val,
                    apply_shading=hillshade.get("value", False),
                ).layer
            ]

        @app.callback(
            Output(self.ids("fence-view"), "figure"),
            [
                Input(self.ids("map-view"), "polyline_points"),
                Input(self.ids("cube"), "value"),
                Input(self.ids("surface"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
            ],
        )
        def _render_fence(coords, cubepath, surfacepath, color_values, colorscale):
            if not coords:
                raise PreventUpdate
            cube = load_cube_data(get_path(cubepath))
            fence = get_fencespec(coords)
            hmin, hmax, vmin, vmax, values = cube.get_randomline(fence)

            surface = xtgeo.surface_from_file(get_path(surfacepath))
            s_arr = get_surface_fence(fence, surface)
            return make_heatmap(
                values,
                s_arr=s_arr,
                theme=self.plotly_theme,
                s_name=self.surfacenames[self.surfacefiles.index(surfacepath)],
                colorscale=colorscale,
                xmin=hmin,
                xmax=hmax,
                ymin=vmin,
                ymax=vmax,
                zmin=color_values[0],
                zmax=color_values[1],
                xaxis_title="Distance along polyline",
                yaxis_title=self.zunit,
            )

        @app.callback(
            [
                Output(self.ids("color-values"), "min"),
                Output(self.ids("color-values"), "max"),
                Output(self.ids("color-values"), "value"),
                Output(self.ids("color-values"), "step"),
            ],
            [Input(self.ids("color-range-btn"), "n_clicks")],
            [State(self.ids("cube"), "value")],
        )
        def _update_color_slider(_clicks, cubepath):

            cube = load_cube_data(get_path(cubepath))
            minv = float(f"{cube.values.min():2f}")
            maxv = float(f"{cube.values.max():2f}")
            value = [minv, maxv]
            step = calculate_slider_step(minv, maxv, steps=100)
            return minv, maxv, value, step

    def add_webvizstore(self):
        return [(get_path, [{"path": fn}]) for fn in self.segyfiles + self.surfacefiles]


# pylint: disable=too-many-arguments, too-many-locals
def make_heatmap(
    arr,
    s_arr,
    theme,
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
    text=None,
    title=None,
    yaxis_title=None,
    xaxis_title=None,
):

    x_inc = (xmax - xmin) / arr.shape[1]
    y_inc = (ymax - ymin) / arr.shape[0]
    colors = (
        [[i / (len(colorscale) - 1), color] for i, color in enumerate(colorscale)]
        if colorscale
        else "RdBu"
    )

    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "height": height,
            "title": title,
            "uirevision": uirevision,
            "margin": {"b": 50, "t": 50, "r": 0},
            "yaxis": {
                "title": yaxis_title,
                "autorange": "reversed" if reverse_y else None,
            },
            "xaxis": {"title": xaxis_title},
        }
    )
    return {
        "data": [
            {
                "type": "heatmap",
                "name": "seismic",
                "text": text,
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
                "name": s_name,
                "marker": {"color": s_color},
            },
        ],
        "layout": layout,
    }


@webvizstore
def get_path(path) -> Path:
    return Path(path)


def get_fencespec(coords):
    """Create a XTGeo fence spec from polyline coordinates"""
    poly = xtgeo.Polygons()
    poly.dataframe = pd.DataFrame(
        [
            {
                "X_UTME": c[1],
                "Y_UTMN": c[0],
                "Z_TVDSS": 0,
                "POLY_ID": 1,
                "NAME": "polyline",
            }
            for c in coords
        ]
    )
    return poly.get_fence(asnumpy=True)
