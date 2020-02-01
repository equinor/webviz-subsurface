from uuid import uuid4
from pathlib import Path
import json

import numpy as np

import dash_table
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html

from webviz_config import WebvizPluginABC
from webviz_subsurface_components import LayeredMap
from webviz_subsurface._datainput.image_processing import (
    get_colormap,
    array_to_png,
)
from webviz_subsurface._datainput.fmu_input import get_realizations, find_surfaces
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
        ensembles = get_realizations(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )

        self._ensembles = ensembles
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
    def layout(self):
        return html.Div(
            style=self.set_grid_layout("1fr 2fr"),
            children=[
                self.selector.layout,
                LayeredMap(
                    id=self.uuid("map"), height=600, layers=[], hillShading=True,
                ),
            ],
        )

    def set_callbacks(self, app):
        pass
        @app.callback(
                Output(self.uuid('map'), "layers"),
            [Input(self.selector.storage_id, "children")],
        )
        def _set_base_layer(surface):
            if not surface:
                raise PreventUpdate
            surface = json.loads(surface)
            print(surface)
            raise PreventUpdate
            # return set_base_layer(self._ensembles, surface)


def get_runpath(ensembles, ensemble, realization):
    """Returns the local runpath for a given ensemble and realization"""
    return Path(
        ensembles.loc[
            (ensembles["ENSEMBLE"] == ensemble) & (ensembles["REAL"] == realization)
        ]["RUNPATH"].item()
    )


def get_surface_stem(name, attribute, date=None):
    """Returns the name of a surface as stored on disk (FMU standard)"""
    return f"{name}--{attribute}--{date}.gri" if date else f"{name}--{attribute}.gri"


def set_base_layer(ensembles, surface):
    """Creates a LayeredMap surface base layer from a SurfaceSelector"""

    # List of surface file paths
    fns = [
        str(
            get_runpath(ensembles, surface["ensemble"], real)
            / "share"
            / "results"
            / "maps"
            / get_surface_stem(surface["name"], surface["attribute"], surface["date"])
        )
        for real in surface["realization"]
    ]

    aggregation = surface["aggregation"]

    # Calculate surface arrays
    # surface_stat = calculate_surface_statistics(fns)
    surface_stat = None

    first_real = surface_stat["template"]

    bounds = [
        [np.min(first_real[0]), np.min(first_real[1])],
        [np.max(first_real[0]), np.max(first_real[1])],
    ]

    center = [np.mean(first_real[0]), np.mean(first_real[1])]

    z_arr = surface_stat[aggregation] if aggregation else first_real

    layer = {
        "name": surface["name"],
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "allowHillshading": True,
                "type": "image",
                "url": array_to_png(z_arr[2].copy()),
                "colormap": get_colormap("viridis"),
                "bounds": bounds,
                "minvalue": f"{z_arr[2].min():.2f}",
                "maxvalue": f"{z_arr[2].max():.2f}",
            }
        ],
    }
    return [layer], bounds, center
