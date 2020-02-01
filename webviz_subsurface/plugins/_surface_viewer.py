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

    @property
    def ensemble_layout(self):
        return html.Div(
            children=[
                html.P("Ensemble"),
                html.Div(
                    children=[
                        dcc.Dropdown(
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles[0],
                            id=self.uuid("ensemble"),
                            clearable=False,
                        )
                    ]
                ),
            ]
        )

    @property
    def realization_layout(self):
        return html.Div(
            children=[
                html.P("Realization"),
                html.Div(
                    children=[
                        dcc.Dropdown(
                            options=[
                                {"label": real, "value": real}
                                for real in self.realizations(self.ensembles[0])
                            ],
                            value=self.realizations(self.ensembles[0])[0],
                            id=self.uuid("realizations"),
                            clearable=False,
                        )
                    ]
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 2fr"),
            children=[
                html.Div(
                    [
                        self.selector.layout,
                        self.ensemble_layout,
                        self.realization_layout,
                    ]
                ),
                LayeredMap(
                    id=self.uuid("map"), height=600, layers=[], hillShading=True
                ),
            ],
        )

    def set_callbacks(self, app):
        pass

        @app.callback(
            Output(self.uuid("map"), "layers"),
            [
                Input(self.selector.storage_id, "children"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realizations"), "value"),
            ],
        )
        def _set_base_layer(data, ensemble, real):
            if not data:
                raise PreventUpdate
            data = json.loads(data)
            runpath = Path(
                self.ens_df.loc[
                    (self.ens_df["ENSEMBLE"] == ensemble)
                    & (self.ens_df["REAL"] == real)
                ]["RUNPATH"].unique()[0]
            )
            filepath = runpath / "share" / "results" / "maps" / f"{data}.gri"
            surface = xtgeo.RegularSurface(str(filepath))
            hillshading = True
            min_val = None
            max_val = None
            color = "viridis"
            s_layer = make_surface_layer(
                surface,
                name="surface",
                min_val=min_val,
                max_val=max_val,
                color=color,
                hillshading=hillshading,
            )
            return [s_layer]
            raise PreventUpdate
            # return set_base_layer(self._ensembles, surface)
