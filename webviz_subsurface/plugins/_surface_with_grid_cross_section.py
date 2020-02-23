from uuid import uuid4
from pathlib import Path
from typing import List

import pandas as pd
from matplotlib.colors import ListedColormap
import xtgeo
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.utils import calculate_slider_step

from .._datainput.grid import load_grid, load_grid_parameter
from .._datainput.surface import make_surface_layer, get_surface_fence


class SurfaceWithGridCrossSection(WebvizPluginABC):
    """### SurfaceWithGridCrossSection

This plugin visualizes surfaces in a map view and grid parameters in a cross section view.
The cross section is defined by a polyline interactively edited in the map view.

NOTE: This is an experimental plugin exploring how we can visualize 3D grid data in Webviz.
The performance is currently slow for large grids.

* `gridfile`: Path to grid geometry (ROFF format)
* `gridparameterfiles`: List of file paths to grid parameters (ROFF format)
* `gridparameternames`: Corresponding list of displayed parameter names
* `surfacefiles`: List of file paths to Irap Binary surfaces
* `surfacenames`: Corresponding list of displayed surface names
* `zunit`: z-unit for display
* `colors`: List of colors to use
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        gridfile: Path,
        gridparameterfiles: List[Path],
        surfacefiles: List[Path],
        gridparameternames: list = None,
        surfacenames: list = None,
        zunit="depth (m)",
        colors: list = None,
    ):

        super().__init__()
        self.zunit = zunit
        self.gridfile = str(gridfile)
        self.gridparafiles = [str(gridfile) for gridfile in gridparameterfiles]
        self.surfacefiles = [str(surffile) for surffile in surfacefiles]
        if surfacenames is not None:
            if len(surfacenames) != len(surfacefiles):
                raise ValueError(
                    "List of surface names specified should be same length as list of surfacefiles"
                )
            self.surfacenames = surfacenames
        else:
            self.surfacenames = [Path(surfacefile).stem for surfacefile in surfacefiles]
        if gridparameternames is not None:
            if len(gridparameternames) != len(gridparameterfiles):
                raise ValueError(
                    "List of grid parameter names specified should be same length "
                    "as list of gridparameterfiles"
                )
            self.gridparanames = gridparameternames
        else:
            self.gridparanames = [
                Path(gridfile).stem for gridfile in gridparameterfiles
            ]
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.initial_colors = (
            colors
            if colors is not None
            else [
                "#440154",
                "#482878",
                "#3e4989",
                "#31688e",
                "#26828e",
                "#1f9e89",
                "#35b779",
                "#6ece58",
                "#b5de2b",
                "#fde725",
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
                    "Plugin to display surfaces and random lines from a 3D grid parameter. "
                ),
            },
            {"id": self.ids("surface"), "content": ("The visualized surface."),},
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
                    "Cross section view of the grid parameter along the edited line. "
                    "The view is empty until a random line is drawn in the map view."
                ),
            },
            {
                "id": self.ids("surface-type"),
                "content": (
                    "Display the z-value of the surface (e.g. depth) or "
                    "the grid parameter value where the surface intersect the grid."
                ),
            },
            {
                "id": self.ids("gridparameter"),
                "content": "The visualized grid parameter.",
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
    def surface_layout(self):
        """Layout for surface section"""
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 1fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select surface",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("surface"),
                                    options=[
                                        {"label": name, "value": path}
                                        for name, path in zip(
                                            self.surfacenames, self.surfacefiles
                                        )
                                    ],
                                    value=self.surfacefiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            style={"marginRight": "50px", "marginLeft": "50px"},
                            children=[
                                dcc.RadioItems(
                                    id=self.ids("surface-type"),
                                    options=[
                                        {
                                            "label": "Display surface z-value",
                                            "value": "surface",
                                        },
                                        {
                                            "label": "Display grid parameter value",
                                            "value": "attribute",
                                        },
                                    ],
                                    value="surface",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    children=[
                        html.Div(
                            style={
                                "marginTop": "20px",
                                "height": "800px",
                                "zIndex": -9999,
                            },
                            children=LayeredMap(
                                id=self.ids("map-view"),
                                draw_toolbar_polyline=True,
                                hillShading=True,
                                layers=[],
                            ),
                        )
                    ]
                ),
            ]
        )

    @property
    def grid_layout(self):
        """Layout for color and other settings"""
        return html.Div(
            children=[
                html.Div(
                    style=self.set_grid_layout("3fr 2fr"),
                    children=[
                        html.Div(
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Select grid parameter",
                                ),
                                dcc.Dropdown(
                                    id=self.ids("gridparameter"),
                                    options=[
                                        {"label": name, "value": para}
                                        for name, para in zip(
                                            self.gridparanames, self.gridparafiles
                                        )
                                    ],
                                    value=self.gridparafiles[0],
                                    clearable=False,
                                ),
                            ]
                        ),
                        html.Div(
                            style={"zIndex": 2000},
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Set colorscale",
                                ),
                                wcc.ColorScales(
                                    id=self.ids("color-scale"),
                                    colorscale=self.initial_colors,
                                    nSwatches=12,
                                ),
                            ],
                        ),
                        html.Div(
                            style={
                                "marginRight": "50px",
                                "marginTop": "20px",
                                "marginLeft": "50px",
                                "marginBottom": "0px",
                            },
                            children=[
                                html.Label(
                                    style={
                                        "font-weight": "bold",
                                        "textAlign": "center",
                                    },
                                    children="Set color range",
                                ),
                                dcc.RangeSlider(
                                    id=self.ids("color-values"),
                                    tooltip={"always_visible": True},
                                ),
                            ],
                        ),
                        html.Button(
                            id=self.ids("color-range-btn"), children="Reset Range"
                        ),
                    ],
                ),
                html.Div(
                    style={"height": "800px"},
                    children=wcc.Graph(
                        config={"displayModeBar": False}, id=self.ids("fence-view")
                    ),
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            id=self.ids("layout"),
            style=self.set_grid_layout("1fr 1fr"),
            children=[self.surface_layout, self.grid_layout],
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
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("surface"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("gridparameter"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
            ],
        )
        def _render_surface(
            surfacepath, surface_type, gridparameter, color_values, colorscale
        ):

            surface = xtgeo.RegularSurface(str(get_path(surfacepath)))
            hillshading = True
            min_val = None
            max_val = None
            color = "viridis"

            if surface_type == "attribute":
                hillshading = False
                min_val = color_values[0] if color_values else None
                max_val = color_values[1] if color_values else None
                color = ListedColormap(colorscale) if colorscale else "viridis"
                grid = load_grid(str(get_path(self.gridfile)))
                gridparameter = load_grid_parameter(grid, str(get_path(gridparameter)))
                surface.slice_grid3d(grid, gridparameter)
                surface.values = surface.values.filled(0)
                if min_val is not None:
                    surface.values[surface.values < min_val] = min_val
                if max_val is not None:
                    surface.values[surface.values > max_val] = max_val

            s_layer = make_surface_layer(
                surface,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            return [s_layer]

        @app.callback(
            Output(self.ids("fence-view"), "figure"),
            [
                Input(self.ids("map-view"), "polyline_points"),
                Input(self.ids("gridparameter"), "value"),
                Input(self.ids("surface"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
            ],
        )
        def _render_fence(coords, gridparameter, surfacepath, color_values, colorscale):
            if not coords:
                raise PreventUpdate
            grid = load_grid(str(get_path(self.gridfile)))
            gridparameter = load_grid_parameter(grid, str(get_path(gridparameter)))
            fence = get_fencespec(coords)
            hmin, hmax, vmin, vmax, values = grid.get_randomline(
                fence, gridparameter, zincrement=0.5
            )

            surface = xtgeo.RegularSurface(str(get_path(surfacepath)))
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
            [State(self.ids("gridparameter"), "value")],
        )
        def _update_color_slider(_clicks, gridparameter):
            grid = load_grid(str(get_path(self.gridfile)))
            gridparameter = load_grid_parameter(grid, str(get_path(gridparameter)))

            minv = float(f"{gridparameter.values.min():2f}")
            maxv = float(f"{gridparameter.values.max():2f}")
            value = [minv, maxv]
            step = calculate_slider_step(minv, maxv, steps=100)
            return minv, maxv, value, step

    def add_webvizstore(self):
        return [
            (get_path, [{"path": fn}])
            for fn in [self.gridfile] + self.gridparafiles + self.surfacefiles
        ]


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
            "margin": {"b": 50, "t": 0, "r": 0},
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
