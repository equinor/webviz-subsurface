import warnings
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

from webviz_subsurface._utils.perf_timer import PerfTimer

from .._datainput.grid import load_grid, load_grid_parameter
from .._datainput.surface import get_surface_fence

import plotly.graph_objects as go
import dash_core_components as dcc
import numpy as np

import sys

# Insert the local path to the Python library 'rips' used to communicate with ResInsight
# Minimum version of ResInsight and 'rips' is 2021.10.2-dev.03
sys.path.insert(0, "/home/builder/cmakebuild/ResInsight/ApplicationExeCode/Python")
import rips

import shutil


class ResInsightSurfaceWithGridCrossSection(WebvizPluginABC):
    """Visualizes surfaces in 3D mesh component based on a cross section view. \
The cross section is defined by a polyline interactively edited in the map view.

NB: This is a draft prototype to display one possible way to use ResInsight as backend \ 
for 3D visualization on web.

---

* **`gridfile`:** Path to grid geometry (`ROFF` format) (absolute or relative to config file).
* **`gridparameterfiles`:** List of file paths to grid parameters (`ROFF` format) \
 (absolute or relative to config file).
* **`gridparameternames`:** List corresponding to filepaths of displayed parameter names.
* **`surfacefiles`:** List of file paths to surfaces (`irap binary` format) \
 (absolute or relative to config file).
* **`surfacenames`:** List corresponding to file paths of displayed surface names.
* **`zunit`:** z-unit for display.
* **`colors`:** List of hex colors to use. \
Note that apostrophies should be used to avoid that hex colors are read as comments. E.g. \
`'#000000'` for black.

---
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        gridfile: Path,
        gridparameterfiles: List[Path],
        surfacefiles: List[Path],
        resinsight_gridfile: Path,
        gridparameternames: list = None,
        simulationgridparameternames: list = None,
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
        self.plotly_theme = webviz_settings.theme.plotly_theme
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
        self.resinsight_gridfile = str(resinsight_gridfile)

        # TODO: When a test version of ResInsight is available, use apt-get install from ppa test, and then use shutil to locate ResInsight executable
        # resinsight_full_path = shutil.which("ResInsight")
        self.resinsight_full_path = (
            "/home/builder/cmakebuild/ResInsight/ApplicationExeCode/ResInsight"
        )

        self.resinsight_instance = rips.Instance.launch(
            resinsight_executable=self.resinsight_full_path, console=True
        )

        if self.resinsight_instance is None:
            warnings.warn(
                (f"Failed to create ResInsight instance "),
                FutureWarning,
            )
        else:
            case = self.resinsight_instance.project.load_case(self.resinsight_gridfile)
            self.ri_view = case.create_view()

            # Get list of available parameters
            # TODO: Update drop-down
            static_parameters = case.available_properties("STATIC_NATIVE")
            dynamic_parameters = case.available_properties("DYNAMIC_NATIVE")
            self.simulationgridparameternames = dynamic_parameters

            self.time_steps = case.time_steps()

        self.ri_cache_instance = True
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
            {
                "id": self.ids("display-mode"),
                "content": ("Display cross section as perspective or flat"),
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
                            open_details=False,
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
                            open_details=False,
                            children=[
                                wcc.Dropdown(
                                    label="Select grid parameter",
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
                                    tooltip={"always_visible": False},
                                ),
                                html.Button(
                                    id=self.ids("color-range-btn"),
                                    children="Reset Range",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="3D settings",
                            children=[
                                wcc.Dropdown(
                                    label="Simulation grid parameter",
                                    id=self.ids("simulationgridparameter"),
                                    options=[
                                        {"label": text, "value": text}
                                        for text in self.simulationgridparameternames
                                    ],
                                    value="SOIL",
                                    clearable=False,
                                ),
                                wcc.Slider(
                                    label="Time Step",
                                    id=self.ids("sim-grid-time-step"),
                                    min=0,
                                    max=len(self.time_steps) - 1,
                                    step=1,
                                    value=0,
                                ),
                                wcc.RadioItems(
                                    label="Geometry display mode",
                                    id=self.ids("display-mode"),
                                    options=[
                                        {
                                            "label": "Show real 3D intersection",
                                            "value": "FULL_3D",
                                        },
                                        {
                                            "label": "Show flat intersection",
                                            "value": "PROJECTED_TO_PLANE",
                                        },
                                    ],
                                    value="FULL_3D",
                                ),
                                wcc.RadioItems(
                                    label="Cache option",
                                    id=self.ids("ri-cache-instance"),
                                    options=[
                                        {
                                            "label": "Cache simulation case",
                                            "value": True,
                                        },
                                        {
                                            "label": "Reload data on each callback",
                                            "value": False,
                                        },
                                    ],
                                    value=True,
                                ),
                                wcc.RadioItems(
                                    label="Cell Edge Mesh",
                                    id=self.ids("ri-cell-edge-mesh"),
                                    options=[
                                        {
                                            "label": "Show Mesh",
                                            "value": True,
                                        },
                                        {
                                            "label": "Mesh Off",
                                            "value": False,
                                        },
                                    ],
                                    value=True,
                                ),
                                wcc.RadioItems(
                                    label="Fault Mesh",
                                    id=self.ids("ri-fault-mesh"),
                                    options=[
                                        {
                                            "label": "Show Mesh",
                                            "value": True,
                                        },
                                        {
                                            "label": "Mesh Off",
                                            "value": False,
                                        },
                                    ],
                                    value=True,
                                ),
                            ],
                        ),
                        wcc.Frame(
                            highlight=False,
                            style={
                                "height": "400px",
                                "flex": 1,
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
                    ],
                ),
                wcc.Frame(
                    highlight=False,
                    style={
                        "height": "1000px",
                        "flex": 7,
                    },
                    children=[dcc.Graph(id=self.ids("3d-view"))],
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.ids("map-view"), "layers"),
            [
                Input(self.ids("surface"), "value"),
                Input(self.ids("surface-type"), "value"),
                Input(self.ids("gridparameter"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("map-view"), "switch"),
            ],
        )
        def _render_surface(
            surfacepath,
            surface_type,
            gridparameter,
            color_values,
            hillshade,
        ):

            surface = xtgeo.surface_from_file(get_path(surfacepath))
            min_val = None
            max_val = None

            if surface_type == "attribute":
                min_val = color_values[0] if color_values else None
                max_val = color_values[1] if color_values else None
                grid = load_grid(get_path(self.gridfile))
                gridparameter = load_grid_parameter(grid, get_path(gridparameter))
                surface.slice_grid3d(grid, gridparameter)

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
            [
                Output(self.ids("3d-view"), "figure"),
            ],
            [
                Input(self.ids("map-view"), "polyline_points"),
                Input(self.ids("simulationgridparameter"), "value"),
                Input(self.ids("color-values"), "value"),
                Input(self.ids("color-scale"), "colorscale"),
                Input(self.ids("display-mode"), "value"),
                Input(self.ids("ri-cache-instance"), "value"),
                Input(self.ids("sim-grid-time-step"), "value"),
                Input(self.ids("ri-cell-edge-mesh"), "value"),
                Input(self.ids("ri-fault-mesh"), "value"),
            ],
        )
        def _render_fence(
            coords,
            simulationgridparameter,
            color_values,
            colorscale,
            geotype,
            ri_cache_instance,
            sim_grid_time_step,
            ri_show_mesh,
            ri_show_fault_mesh,
        ):
            if not coords:
                raise PreventUpdate

            timer = PerfTimer()

            if ri_cache_instance == False:
                self.resinsight_instance = None

            # Create ResInsight instance
            if self.resinsight_instance is None:
                self.resinsight_instance = rips.Instance.launch(
                    resinsight_executable=self.resinsight_full_path, console=True
                )

                if self.resinsight_instance is None:
                    warnings.warn(
                        (f"Failed to create ResInsight instance "),
                        FutureWarning,
                    )
                else:
                    case = self.resinsight_instance.project.load_case(
                        self.resinsight_gridfile
                    )
                    self.ri_view = case.create_view()

                ri_timer_load_case = timer.lap_ms()
                print(
                    "{} : {}".format(
                        "Create instance and load case", ri_timer_load_case
                    )
                )

            ri_x = []
            ri_y = []
            ri_z = []
            ri_i = []
            ri_j = []
            ri_k = []
            ri_mesh_x = []
            ri_mesh_y = []
            ri_mesh_z = []
            ri_fault_mesh_x = []
            ri_fault_mesh_y = []
            ri_fault_mesh_z = []

            if self.resinsight_instance is not None:

                # Set simulation grid time step
                self.ri_view.set_time_step(sim_grid_time_step)

                intersection_coll = self.resinsight_instance.project.descendants(
                    rips.IntersectionCollection
                )[0]

                # Create intersection based on coord from UI
                ri_coords = []
                for c in coords:
                    coord = [c[1], c[0], 1500.0]
                    ri_coords.append(coord)

                intersection = intersection_coll.add_new_object(rips.CurveIntersection)
                intersection.points = ri_coords
                intersection.update()

                ri_timer_create_intersection = timer.lap_ms()
                print(
                    "{} : {}".format(
                        "Create intersection", ri_timer_create_intersection
                    )
                )

                # Get geometry and result values from ResInsight
                geometry = intersection.geometry(geometry_type=geotype)

                result = self.get_result_values(
                    result_type="DYNAMIC_NATIVE",
                    result_variable=simulationgridparameter,
                    intersection=intersection,
                    geotype=geotype,
                )

                ri_timer_read_from_ri = timer.lap_ms()
                print("{} : {}".format("Read data from RI", ri_timer_read_from_ri))

                # get IJK values
                index_i = self.get_result_values(
                    result_type="STATIC_NATIVE",
                    result_variable="INDEX_I",
                    intersection=intersection,
                    geotype=geotype,
                )
                index_j = self.get_result_values(
                    result_type="STATIC_NATIVE",
                    result_variable="INDEX_J",
                    intersection=intersection,
                    geotype=geotype,
                )
                index_k = self.get_result_values(
                    result_type="STATIC_NATIVE",
                    result_variable="INDEX_K",
                    intersection=intersection,
                    geotype=geotype,
                )

                hover_text_per_vertex = []
                for i in range(len(index_i)):
                    text = (
                        "IJK ["
                        + str(index_i[i])
                        + ", "
                        + str(index_j[i])
                        + ", "
                        + str(index_k[i])
                        + "]"
                    )
                    hover_text_per_vertex.append(text)
                    hover_text_per_vertex.append(text)
                    hover_text_per_vertex.append(text)

                result_per_vertex = []
                for res_val in result:
                    result_per_vertex.append(res_val)
                    result_per_vertex.append(res_val)
                    result_per_vertex.append(res_val)

                ri_x = geometry.x_coords
                ri_y = geometry.y_coords
                ri_z = geometry.z_coords

                ri_mesh_x = geometry.mesh_x_coords
                ri_mesh_y = geometry.mesh_y_coords
                ri_mesh_z = geometry.mesh_z_coords

                ri_fault_mesh_x = geometry.fault_mesh_x_coords
                ri_fault_mesh_y = geometry.fault_mesh_y_coords
                ri_fault_mesh_z = geometry.fault_mesh_z_coords

                # Set Fault mesh to empty array due to bug in empty container
                if len(ri_fault_mesh_x) < 2:
                    ri_fault_mesh_x = []
                    ri_fault_mesh_y = []
                    ri_fault_mesh_z = []

                # Geometry is given in display coordinates, and must be adjusted to domain coords
                if geotype == "FULL_3D":
                    offset = geometry.display_model_offset
                    for i in range(len(ri_x)):
                        ri_x[i] += offset[0]
                        ri_y[i] += offset[1]
                        ri_z[i] += offset[2]

                    for i in range(len(ri_mesh_x)):
                        ri_mesh_x[i] += offset[0]
                        ri_mesh_y[i] += offset[1]
                        ri_mesh_z[i] += offset[2]

                    for i in range(len(ri_fault_mesh_x)):
                        ri_fault_mesh_x[i] += offset[0]
                        ri_fault_mesh_y[i] += offset[1]
                        ri_fault_mesh_z[i] += offset[2]

                triangle_count = int(len(geometry.connections) / 3)
                for res_val in range(triangle_count):
                    ri_i.append(geometry.connections[res_val * 3 + 0])
                    ri_j.append(geometry.connections[res_val * 3 + 1])
                    ri_k.append(geometry.connections[res_val * 3 + 2])

                print("{} : {}".format("Triangle count", triangle_count))

            create_mesh3d_ms = timer.lap_ms()
            print("\n{} : {}".format("Create mesh3d", create_mesh3d_ms))

            # Create edge coordinates, separate by None to avoid connection between two triangles
            # The datastructure from ResInsight defines pairs of coordinates used to create a line along a cell edge
            mesh_x = []
            mesh_y = []
            mesh_z = []
            if ri_show_mesh:
                for i in range(len(ri_mesh_x)):
                    if (i % 2) == 0:
                        mesh_x.append(None)
                        mesh_y.append(None)
                        mesh_z.append(None)

                    mesh_x.append(ri_mesh_x[i])
                    mesh_y.append(ri_mesh_y[i])
                    mesh_z.append(ri_mesh_z[i])

            # define the trace for triangle sides
            cell_mesh_lines = go.Scatter3d(
                x=mesh_x,
                y=mesh_y,
                z=mesh_z,
                mode="lines",
                name="",
                line=dict(color="rgb(200,200,200)", width=3),
            )

            # Create edge coordinates, separate by None to avoid connection between two triangles
            # The datastructure from ResInsight defines pairs of coordinates used to create a line along a cell edge
            fault_mesh_x = []
            fault_mesh_y = []
            fault_mesh_z = []
            if ri_show_fault_mesh:
                for i in range(len(ri_fault_mesh_x)):
                    if (i % 2) == 0:
                        fault_mesh_x.append(None)
                        fault_mesh_y.append(None)
                        fault_mesh_z.append(None)

                    fault_mesh_x.append(ri_fault_mesh_x[i])
                    fault_mesh_y.append(ri_fault_mesh_y[i])
                    fault_mesh_z.append(ri_fault_mesh_z[i])

            # define the trace for triangle sides
            fault_mesh_lines = go.Scatter3d(
                x=fault_mesh_x,
                y=fault_mesh_y,
                z=fault_mesh_z,
                mode="lines",
                name="",
                line=dict(color="rgb(50,50,50)", width=5),
            )

            camera = dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=1.25, y=1.25, z=1.25),
                projection=dict(type="perspective"),
            )

            dragmode = "turntable"
            if geotype == "PROJECTED_TO_PLANE":
                dragmode = "pan"
                camera = dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=0, y=-1.5, z=0),
                    projection=dict(type="orthographic"),
                )

            my_fig = {
                "data": [
                    {
                        "colorbar": {
                            "title": {"text": simulationgridparameter},
                            "lenmode": "pixels",
                            "len": 200,
                        },
                        "intensity": result_per_vertex,
                        "i": ri_i,
                        "j": ri_j,
                        "k": ri_k,
                        "name": "y",
                        "showscale": True,
                        "type": "mesh3d",
                        "x": ri_x,
                        "y": ri_y,
                        "z": ri_z,
                        "hovertext": hover_text_per_vertex,
                    },
                    cell_mesh_lines,
                    fault_mesh_lines,
                ],
                "layout": {
                    "margin": {"b": 10, "l": 10, "r": 20, "t": 50},
                    "scene": {
                        "xaxis": {"nticks": 6, "range": [min(ri_x), max(ri_x)]},
                        "yaxis": {"nticks": 6, "range": [min(ri_y), max(ri_y)]},
                        "zaxis": {"nticks": 6, "range": [min(ri_z), max(ri_z)]},
                        "camera": camera,
                    },
                    "template": "...",
                    "height": 1000,
                    "width": 1200,
                    "dragmode": dragmode,
                    "paper_bgcolor": "rgb( 180, 196, 221 )",
                },
            }

            ri_timer_create_my_fig = timer.lap_ms()
            print(
                "{} : {}".format(
                    "Prepare Mesh3D object for display ", ri_timer_create_my_fig
                )
            )

            return (my_fig,)

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
            grid = load_grid(get_path(self.gridfile))
            gridparameter = load_grid_parameter(grid, get_path(gridparameter))

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

    def get_result_values(self, result_type, result_variable, intersection, geotype):
        self.ri_view.apply_cell_result(
            result_type=result_type,
            result_variable=result_variable,
        )
        return intersection.geometry_result(geometry_type=geotype).values


@webvizstore
def get_path(path) -> Path:
    return Path(path)
