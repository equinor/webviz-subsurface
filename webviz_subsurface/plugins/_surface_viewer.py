from uuid import uuid4
from pathlib import Path
import json

import numpy as np
import xtgeo
import dash_table
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

from webviz_config import WebvizPluginABC
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_subsurface._datainput.image_processing import get_colormap, array_to_png
from webviz_subsurface._datainput.fmu_input import get_realizations, find_surfaces
from .._datainput.surface import make_surface_layer
from webviz_subsurface._private_plugins.surface_selector import SurfaceSelector


class SurfaceViewer(WebvizPluginABC):
    """### SurfaceViewer

Viewer for FMU surfaces. Automatically finds all surfaces for a given
scratch ensembleset. Allows viewing of individual realizations or aggregations.
"""

    def __init__(self, app, ensembles):

        super().__init__()
        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }

        # Find surfaces
        self.config = find_surfaces(self.ens_paths)
        # Extract realizations and sensitivity information
        self.ens_df = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )
        self._storage_id = f"{str(uuid4())}-surface-viewer"
        self._map_id = f"{str(uuid4())}-map-id"
        self.selector = SurfaceSelector(app, self.config, ensembles)
        self.selector2 = SurfaceSelector(app, self.config, ensembles)
        self.selector3 = SurfaceSelector(app, self.config, ensembles)
        self.set_callbacks(app)

    def add_webvizstore(self):
        return [
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ]

    @property
    def ensembles(self):
        return list(self.ens_df["ENSEMBLE"].unique())

    def realizations(self, ensemble, sensname=None, senstype=None):
        df = self.ens_df.loc[self.ens_df["ENSEMBLE"] == ensemble].copy()
        if sensname and senstype:
            df = df.loc[(df["SENSNAME"] == sensname) & (df["SENSCASE"] == senstype)]
        return list(df["REAL"])

    @property
    def map_id(self):
        return self._map_id

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    # @property
    # def surface_table(self):
    #     return dash_table.DataTable(
    #         id=self.uuid("table"),
    #         columns=[{"name": i, "id": i, 'hidden':True if i == 'path' else False} for i in self.config.columns],
    #         data=self.config.to_dict("rows"),
    #         sort_action="native",
    #         filter_action="native",
    #         page_action="native",
    #         selected_rows=[0],
    #     )

    def ensemble_layout(self, ensId, realId):
        return wcc.FlexBox(
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        html.Div(
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    id=ensId,
                                    clearable=False,
                                )
                            ]
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label("Realization"),
                        html.Div(
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.realizations(self.ensembles[0])[0],
                                    id=realId,
                                    clearable=False,
                                )
                            ]
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self):
        return wcc.FlexBox(
            style={"fontSize": ".9rem"},
            children=[
                html.Div(
                    style={"margin": "10px", "flex": 4},
                    children=[
                        self.selector.layout,
                        self.ensemble_layout(
                            self.uuid("ensemble"), self.uuid("realization")
                        ),
                        LayeredMap(
                            sync_ids=[self.uuid('map2'), self.uuid('map3')],
                            id=self.uuid("map"), height=600, layers=[], hillShading=True
                        ),
                    ],
                ),
                html.Div(
                    style={"margin": "10px", "flex": 4},
                    children=[
                        self.selector2.layout,
                        self.ensemble_layout(
                            self.uuid("ensemble2"), self.uuid("realization2")
                        ),
                        LayeredMap(
                            sync_ids=[self.uuid('map'), self.uuid('map3')],
                            id=self.uuid("map2"),
                            height=600,
                            layers=[],
                            hillShading=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"margin": "10px", "flex": 4},
                    children=[
                        html.Label("Lock name"),
                        html.Div(dcc.Dropdown()),
                        html.Label("Lock attribute"),
                        html.Div(dcc.Dropdown()),
                        html.Label("Lock date"),
                        html.Div(dcc.Dropdown()),
                        html.Label("Calculation"),
                        html.Div(
                            dcc.Dropdown(
                                id=self.uuid("calculation"),
                                value="Difference",
                                clearable=False,
                                options=[
                                    {"label": i, "value": i}
                                    for i in [
                                        "Difference",
                                        "Sum",
                                        "Product",
                                        "Quotient",
                                    ]
                                ],
                            )
                        ),
                        LayeredMap(
                            sync_ids=[self.uuid('map'), self.uuid('map2')],
                            id=self.uuid("map3"),
                            height=600,
                            layers=[],
                            hillShading=True,
                        ),
                    ],
                ),
            ],
        )

    def get_runpath(self, data, ensemble, real):
        data = json.loads(data)
        runpath = Path(
            self.ens_df.loc[
                (self.ens_df["ENSEMBLE"] == ensemble) & (self.ens_df["REAL"] == real)
            ]["RUNPATH"].unique()[0]
        )
        return str(runpath / "share" / "results" / "maps" / f"{data}.gri")

    def set_callbacks(self, app):
        pass

        @app.callback(
            [
                Output(self.uuid("map"), "layers"),
                Output(self.uuid("map2"), "layers"),
                Output(self.uuid("map3"), "layers"),
            ],
            [
                Input(self.selector.storage_id, "children"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realization"), "value"),
                Input(self.selector2.storage_id, "children"),
                Input(self.uuid("ensemble2"), "value"),
                Input(self.uuid("realization"), "value"),
                Input(self.uuid("calculation"), "value"),
            ],
        )
        def _set_base_layer(data, ensemble, real, data2, ensemble2, real2, calculation):
            if not data or not data2:
                raise PreventUpdate
            surface = xtgeo.RegularSurface(self.get_runpath(data, ensemble, real))
            surface2 = xtgeo.RegularSurface(self.get_runpath(data2, ensemble2, real2))

            surface3 = surface.copy()
            try:
                if calculation == 'Difference':
                    surface3.values = surface3.values - surface2.values
                if calculation == 'Sum':
                    surface3.values = surface3.values + surface2.values
                if calculation == 'Product':
                    surface3.values = surface3.values * surface2.values
                if calculation == 'Quotient':
                    surface3.values = surface3.values / surface2.values
                layers3 = [make_surface_layer(surface3, name="surface", color="viridis", hillshading=True)]
            except ValueError:
                layers3 = []

            surface_layer = make_surface_layer(surface, name="surface", color="viridis", hillshading=True)
            surface_layer2 = make_surface_layer(surface2, name="surface", color="viridis", hillshading=True)
            
            return [surface_layer], [surface_layer2], layers3

