from uuid import uuid4
from pathlib import Path
import json
import io

import numpy as np
import xtgeo
import dash_table
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
import webviz_core_components as wcc
from webviz_subsurface_components import LayeredMap
from webviz_subsurface._datainput.image_processing import get_colormap, array_to_png
from webviz_subsurface._datainput.fmu_input import get_realizations, find_surfaces
from .._datainput.surface import make_surface_layer, get_surface_arr
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
        reals = list(df["REAL"])
        reals.extend(["Mean", "StdDev", "Min", "Max"])
        return reals

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
                        wcc.Graph(
                            # sync_ids=[self.uuid("map2"), self.uuid("map3")],
                            id=self.uuid("map"),
                            # height=600,
                            # layers=[],
                            # hillShading=True,
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
        
        return str(
            get_path(str(runpath / "share" / "results" / "maps" / f"{data}.gri"))
        )

    def get_ens_runpath(self, data, ensemble):
        data = json.loads(data)
        runpaths = self.ens_df.loc[(self.ens_df["ENSEMBLE"] == ensemble)][
            "RUNPATH"
        ].unique()
        return [
            str((Path(runpath) / "share" / "results" / "maps" / f"{data}.gri"))
            for runpath in runpaths
        ]

    def set_callbacks(self, app):
        pass

        @app.callback(
            Output(self.uuid("map"), "figure"),
            [
                Input(self.selector.storage_id, "children"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("realization"), "value"),
            ],
        )
        def _set_base_layer(data, ensemble, real):
            from timeit import default_timer as timer
            start = timer()
            if not data:
                raise PreventUpdate
            if real in ["Mean", "StdDev", "Min", "Max"]:
                surface = xtgeo.RegularSurface().from_file(
                    calculate_surface(self.get_ens_runpath(data, ensemble), real)
                )
            else:
                surface = xtgeo.RegularSurface(self.get_runpath(data, ensemble, real))

            import plotly.express as px
            


            arr = get_surface_arr(surface)[2]

            # fig = px.imshow(get_surface_arr(surface)[2])
            fig = {
                "data": [
                    {
                        "coloraxis": "coloraxis",
                        "type": "heatmap",
                        "z": arr,
                    }
                ],
                "layout": {"margin": {"t": 60},
                    "template": "...",
                    "xaxis": {"constrain": "domain", "scaleanchor": "y"},
                    "yaxis": {"autorange": "reversed", "constrain": "domain"},
                },
            }

            end = timer()
            
            return fig

    def add_webvizstore(self):
        store_functions = []
        filenames = []
        # Generate all file names
        for attr, values in self.config.items():
            for name in values["names"]:
                
                for date in values["dates"]:

                    filename = f"{name}--{attr}"
                    if date is not None:
                        filename += f"--{date}"
                    filename += f".gri"
                    
                    filenames.append(filename)
        # Copy all realization files
        for runpath in self.ens_df["RUNPATH"].unique():
            for filename in filenames:
                path = Path(runpath) / "share" / "results" / "maps" / filename
                if path.exists():
                    store_functions.append((get_path, [{"path": str(path)}],))

        # Calculate and store statistics
        for ens, ens_df in self.ens_df.groupby("ENSEMBLE"):
            runpaths = list(ens_df["RUNPATH"].unique())
            for filename in filenames:
                paths = [
                    str(Path(runpath) / "share" / "results" / "maps" / filename)
                    for runpath in runpaths
                ]
                for statistic in ["Mean", "StdDev", "Min", "Max"]:
                    store_functions.append(
                        (calculate_surface, [{"fns": paths, "statistic": statistic}],)
                    )
                    

        store_functions.append(
            (
                get_realizations,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        )
        return store_functions


# @CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def calculate_surface(fns, statistic) -> io.BytesIO:
    surfaces = xtgeo.Surfaces(fns)
    stream = io.BytesIO()
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface()
        surface.to_file(stream)
        return stream
    if statistic == "Mean":
        surface = surfaces.apply(np.nanmean, axis=0)
    if statistic == "StdDev":
        surface = surfaces.apply(np.nanstd, axis=0)
    if statistic == "Min":
        surface = surfaces.apply(np.nanmin, axis=0)
    if statistic == "Max":
        surface = surfaces.apply(np.nanmax, axis=0)
    if statistic == "P10":
        surface = surfaces.apply(np.nanpercentile, 10, axis=0)
    if statistic == "P90":
        surface = surfaces.apply(np.nanpercentile, 90, axis=0)

    surface.to_file(stream)
    return stream


@webvizstore
def get_path(path) -> Path:
    
    return Path(path)
