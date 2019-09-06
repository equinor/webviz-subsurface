import os
import glob
from uuid import uuid4
from glob import glob
from pathlib import PurePath
from collections import OrderedDict
import numpy as np
import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from dash_table import DataTable
from webviz_config.common_cache import cache
from webviz_config.containers import WebvizContainer
from webviz_subsurface.datainput.leaflet import (
    LeafletSurface,
    SurfaceCollection,
    LeafletCrossSection,
)
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from fmu.ensemble import ScratchEnsemble
import xtgeo
import plotly.express as px


class StructuralUncertainty(WebvizContainer):
    """### StructuralUncertainty

This container visualizes surfaces intersected along a well path.
The input are surfaces from a FMU ensemble stored on standardized
format with standardized naming (share/results/maps/name--category.gri)
and a folder of well files stored in RMS well format.

* `ensemble`: Which ensemble in `container_settings` to visualize.
* `well_path`: File folder with wells in rmswell format
* `surface_cat`: Surface category to look for in the file names
* `surface_names`: List of surface names to look for in the file names
* `well_suffix`:  Optional suffix for well files. Default is .rmswell
"""

    def __init__(
        self,
        app,
        container_settings,
        ensemble,
        surface_names : list,
        surface_categories : list,
    ):

        self.ens = ScratchEnsemble(
            ensemble, container_settings["scratch_ensembles"][ensemble]
        )
        self.real_paths = [
            os.path.join(obj._origpath, "share", "results", "maps")
            for real, obj in self.ens._realizations.items()
        ]
        self.reals = [str(real) for real, obj in self.ens._realizations.items()]
        self.cat = surface_categories
        self.calculations = ["Mean", "StdDev", "Min", "Max"]
        self.strat = surface_names
        self.map_id = str(uuid4())
        self.fence_id = str(uuid4())
        self.chart_id = str(uuid4())
        self.calc_id = str(uuid4())
        self.s_name_id = str(uuid4())
        self.s_cat_id = str(uuid4())
        self.s_name_id2 = str(uuid4())
        self.s_cat_id2 = str(uuid4())
        self.well_id = str(uuid4())
        self.s_cats = surface_categories
        self.s_names = surface_names
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
                            options=[{"value": cat, "label": cat} for cat in self.cat],
                            value=self.cat[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_name_id,
                            options=[
                                {"value": cat, "label": cat} for cat in self.strat
                            ],
                            value=self.strat[0],
                        ),
                        dcc.RadioItems(
                            id=self.calc_id,
                            options=[
                                {"value": calc, "label": calc}
                                for calc in self.calculations
                            ],
                            value=self.calculations[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_cat_id2,
                            options=[{"value": cat, "label": cat} for cat in self.cat],
                            value=self.cat[0],
                        ),
                        dcc.Dropdown(
                            id=self.s_name_id2,
                            options=[
                                {"value": cat, "label": cat} for cat in self.strat
                            ],
                            value=self.strat[0],
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
        def change_map(calc_type, s_name, s_cat):
            stratsurfs = {}
            stratsurfs[f"{s_name}"] = [
                str(os.path.join(r, f"{s_name}--{s_cat}.gri")) for r in self.real_paths
            ]
            collection = SurfaceCollection(stratsurfs)
            stat_surfs = {}
            stat_surfs["Mean"] = collection.apply(s_name, np.nanmean, axis=0)
            stat_surfs["Min"] = collection.apply(s_name, np.nanmin, axis=0)
            stat_surfs["Max"] = collection.apply(s_name, np.nanmax, axis=0)
            stat_surfs["StdDev"] = collection.apply(s_name, np.nanstd, axis=0, ddof=1)

            sleaf = LeafletSurface(s_name, stat_surfs[calc_type])
            return [sleaf.leaflet_layer], sleaf.bounds, sleaf.center

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
        def change_fence(coords, s_names, s_cat):
            if not coords:
                return [], [[0, 0], [0, 0]], [0, 0]

            if not isinstance(s_names, list):
                s_names = [s_names]

            stratsurfs = {}
            for s_name in s_names:
                stratsurfs[s_name] = [
                    os.path.join(r, f"{s_name}--{s_cat}.gri") for r in self.real_paths
                ]

            collection = SurfaceCollection(stratsurfs)
            fencespec = get_fencespec(coords)
            sleaf = LeafletCrossSection(fencespec)
            sleaf.set_bounds_and_center(
                collection._surface_collection[s_names[0]].surfaces[0]
            )

            for s_name in s_names:
                s = collection.apply(s_name, np.nanmean, axis=0)
                sleaf.add_surface_layer(
                    surface=s, name=f"{s_name}(Mean)", color="black"
                )
                s = collection.apply(s_name, np.nanmin, axis=0)
                sleaf.add_surface_layer(surface=s, name=f"{s_name}(Min)", color="red")
                s = collection.apply(s_name, np.nanmax, axis=0)
                sleaf.add_surface_layer(surface=s, name=f"{s_name}(Max)", color="blue")

            return sleaf.get_layers(), sleaf.bounds, sleaf.center

        @app.callback(
            Output(self.chart_id, "figure"),
            [
                Input(self.map_id, "marker_point"),
                Input(self.s_name_id, "value"),
                Input(self.s_cat_id, "value"),
            ],
        )
        def change_chart(coords, s_names, s_cat):
            if not coords:
                return {"data": []}
            if not isinstance(s_names, list):
                s_names = [s_names]
            s_name = s_names[0]
            stratsurfs = {}
            stratsurfs[f"{s_name}"] = [
                str(os.path.join(r, f"{s_name}--{s_cat}.gri")) for r in self.real_paths
            ]
            collection = SurfaceCollection(stratsurfs)
            xy = (coords[1], coords[0])
            print(xy)
            data = [
                surf.get_value_from_xy(xy)
                for surf in collection._surface_collection[s_name].surfaces
            ]
            print(data)
            return {"data": [{"x": data, "type": "histogram"}]}


def get_fencespec(coords):
    coords_dict = [{"X_UTME": c[1], "Y_UTMN": c[0], "Z_TVDSS": 0} for c in coords]
    df = pd.DataFrame().from_dict(coords_dict)
    df["POLY_ID"] = 1
    df["NAME"] = "test"
    poly = xtgeo.Polygons()
    poly.dataframe = df
    return poly.get_fence(asnumpy=True)
