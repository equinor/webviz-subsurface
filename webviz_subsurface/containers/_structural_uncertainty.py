import os
from uuid import uuid4
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.containers import WebvizContainer
from webviz_subsurface.datainput.leaflet import (
    LeafletSurface, LeafletCrossSection)
import webviz_subsurface_components as wsc
try:
    from fmu.ensemble import ScratchEnsemble
except ImportError:
    pass
from xtgeo import Surfaces, Polygons


class StructuralUncertainty(WebvizContainer):
    '''### StructuralUncertainty

    This container visualizes statistical surfaces from an ensemble.


    * `ensemble`: Which ensemble in `container_settings` to visualize.
    * `surface_categories`: A list of surface categories
    * `surface_names`: A list of surface names

    '''

    def __init__(
        self,
        app,
        container_settings,
        ensemble,
        surface_names: list,
        surface_categories: list,
    ):

        self.reals, self.real_folders = get_reals(
            ensemble, container_settings["scratch_ensembles"][ensemble]
        )
        self.surface_folder = os.path.join("share", "results", "maps")

        self.s_cats = surface_categories
        self.s_names = surface_names

        self.map_calculations = ["Mean", "StdDev", "Min", "Max"]
        self.fence_calculations = ["Mean", "Min", "Max"]

        self.map_id = str(uuid4())
        self.fence_id = str(uuid4())
        self.chart_id = str(uuid4())
        self.calc_id = str(uuid4())
        self.s_name_id = str(uuid4())
        self.s_cat_id = str(uuid4())
        self.s_name_id2 = str(uuid4())
        self.s_cat_id2 = str(uuid4())
        self.well_id = str(uuid4())

        self.set_callbacks(app)

    @property
    def style_layout(self):
        """Simple grid layout for the selector row"""
        return {
            "display": "grid",
            "align-content": "space-around",
            "justify-content": "space-between",
            "grid-template-columns": "2fr 1fr 2fr",
        }

    @property
    def layout(self):
        return html.Div(
            style=self.style_layout,
            children=[
                html.Div(
                    children=[
                        wsc.LayeredMap(
                            id=self.map_id,
                            map_bounds=[[0, 0], [0, 0]],
                            center=[0, 0],
                            layers=[],
                        )
                    ]
                ),
                html.Div(
                    children=[
                        dcc.Dropdown(
                            id=self.s_cat_id,
                            options=[
                                {"value": cat, "label": cat}
                                for cat in self.s_cats
                            ],
                            value=self.s_cats[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_name_id,
                            options=[
                                {"value": cat, "label": cat}
                                for cat in self.s_names
                            ],
                            value=self.s_names[0],
                        ),
                        dcc.RadioItems(
                            id=self.calc_id,
                            options=[
                                {"value": calc, "label": calc}
                                for calc in self.map_calculations
                            ],
                            value=self.map_calculations[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_cat_id2,
                            options=[
                                {"value": cat, "label": cat}
                                for cat in self.s_cats
                            ],
                            value=self.s_cats[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_name_id2,
                            options=[
                                {"value": cat, "label": cat}
                                for cat in self.s_names
                            ],
                            value=self.s_names[0],
                            multi=True,
                        ),
                        wcc.Graph(self.chart_id),
                    ]
                ),
                wsc.LayeredMap(
                    id=self.fence_id,
                    map_bounds=[[0, 0], [0, 0]],
                    center=[0, 0],
                    layers=[],
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.map_id, "layers"),
                Output(self.map_id, "map_bounds"),
                Output(self.map_id, "center"),
            ],
            [
                Input(self.calc_id, "value"),
                Input(self.s_name_id, "value"),
                Input(self.s_cat_id, "value"),
            ],
        )
        def _change_map(calc_type, s_name, s_cat):
            """Callback to update the visualized map

            Input:
                calc_type: Type of statistical calculation
                s_name: Surface name from dropdown
                s_cat: Surface category from dropdown
            Output:
                layers: A list of leaflet layers
                map_bounds: Bounds for the leaflet component
                center: Center for the leaflet component
            """

            surfaces = get_surfaces_from_scratch(
                self.real_folders, self.surface_folder, s_name, s_cat
            )

            stat_surface = get_statistical_surface(surfaces, calc_type)

            leaf = LeafletSurface(s_name, stat_surface)

            return [leaf.leaflet_layer], leaf.bounds, leaf.center

        @app.callback(
            [
                Output(self.fence_id, "layers"),
                Output(self.fence_id, "map_bounds"),
                Output(self.fence_id, "center"),
            ],
            [
                Input(self.map_id, "line_points"),
                Input(self.s_name_id2, "value"),
                Input(self.s_cat_id2, "value"),
            ],
        )
        def _change_fence(coords, s_names, s_cat):
            """Callback to update the visualized cross-section

            Input:
                coords: Polyline coordinates from map view
                s_names: Surface names from dropdown
                s_cat: Surface category from dropdown
            Output:
                layers: A list of leaflet layers
                map_bounds: Bounds for the leaflet component
                center: Center for the leaflet component
            """

            # If no polyline is digitized, return empty view
            if not coords:
                return [], [[0, 0], [0, 0]], [0, 0]

            if not isinstance(s_names, list):
                s_names = [s_names]

            # Create a fence spec from the marker coords
            fencespec = get_fencespec(coords)

            # Initialize a leaflet cross section
            sleaf = LeafletCrossSection(fencespec)
            has_bounds_center = False

            # Loop through selected surface names and create file paths
            for s_name in s_names:
                surfaces = get_surfaces_from_scratch(
                    self.real_folders, self.surface_folder, s_name, s_cat
                )

                # Sets bounds and center (should be reworked)
                if not has_bounds_center:
                    sleaf.set_bounds_and_center(surfaces.surfaces[0])

                # Create leaflet layer for each statistic calculation
                for calc_type in self.fence_calculations:
                    sleaf.add_surface_layer(
                        surface=get_statistical_surface(surfaces, calc_type),
                        name=f"{s_name}({calc_type})",
                        color="black",
                    )
            return sleaf.get_layers(), sleaf.bounds, sleaf.center

        @app.callback(
            Output(self.chart_id, "figure"),
            [
                Input(self.map_id, "marker_point"),
                Input(self.s_name_id, "value"),
                Input(self.s_cat_id, "value"),
            ],
        )
        def _change_chart(coords, s_name, s_cat):
            """Callback to update the statistical histogram

            Input:
                marker_point: Marker coordinates from map view
                s_name: Surface name from dropdown
                s_cat: Surface category from dropdown
            Output:
                figure: Plotly graph figure
            """

            # If no marker is digitized return empty graph
            if not coords:
                return {"data": []}

            surfaces = get_surfaces_from_scratch(
                self.real_folders, self.surface_folder, s_name, s_cat
            )

            # x, y = y, x - Should look at this in the Leaflet component
            xy = (coords[1], coords[0])

            # Get z-value of all surfaces at given coordinates
            data = [surf.get_value_from_xy(xy) for surf in surfaces.surfaces]

            return {"data": [{"x": data, "type": "histogram"}]}


def get_fencespec(coords):
    '''Create a XTGeo fence spec from polyline coordinates'''
    coords_dict = [{"X_UTME": c[1], "Y_UTMN": c[0], "Z_TVDSS": 0}
                   for c in coords]
    df = pd.DataFrame().from_dict(coords_dict)
    df["POLY_ID"] = 1
    df["NAME"] = "test"
    poly = Polygons()
    poly.dataframe = df
    return poly.get_fence(asnumpy=True)


def get_reals(ens_name, ens_path):
    '''Retrieve valid realization and paths from ens instance'''
    ens = ScratchEnsemble(ens_name, ens_path)
    real_folders = []
    reals = []
    for real, real_obj in ens._realizations.items():
        reals.append(str(real))
        real_folders.append(real_obj._origpath)
    return reals, real_folders


def get_surfaces_from_scratch(
    real_folders: list, surface_folder, s_name, s_cat=None, s_suffix=".gri"
):
    '''Retrieve an XTGeo surfaces instance for an ensemble of surfaces
    on scratch'''

    base_name = f"{s_name}--{s_cat}{s_suffix}"
    surf_paths = [
        os.path.join(r_folder, surface_folder, base_name)
        for r_folder in real_folders
    ]
    return Surfaces(surf_paths)


def get_statistical_surface(surfaces: Surfaces, calc_type="Mean"):
    """Calculate statistial surface from a Xtgeo Surfaces instance"""
    if calc_type == "Mean":
        return surfaces.apply(np.nanmean, axis=0)
    if calc_type == "Min":
        return surfaces.apply(np.nanmin, axis=0)
    if calc_type == "Max":
        return surfaces.apply(np.nanmax, axis=0)
    if calc_type == "StdDev":
        return surfaces.apply(np.nanstd, axis=0, ddof=1)
