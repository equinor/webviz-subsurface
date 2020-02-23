from uuid import uuid4
from pathlib import Path
import json
import io
import os
import logging
import numpy as np
import xtgeo
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc
from webviz_subsurface_components import LayeredMap
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC
import webviz_core_components as wcc

from .._datainput.fmu_input import get_realizations, find_surfaces
from .._datainput.surface import make_surface_layer
from .._private_plugins.surface_selector import SurfaceSelector


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

    def ensemble_layout(
        self, ensemble_id, ens_prev_id, ens_next_id, real_id, real_prev_id, real_next_id
    ):
        return wcc.FlexBox(
            children=[
                html.Div(
                    [
                        html.Label("Ensemble"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    id=ensemble_id,
                                    clearable=False,
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=ens_prev_id,
                                    children="Prev",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=ens_next_id,
                                    children="Next",
                                ),
                            ],
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Label("Realization / Statistic"),
                        html.Div(
                            style=self.set_grid_layout("12fr 1fr 1fr"),
                            children=[
                                dcc.Dropdown(
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations(self.ensembles[0])
                                    ],
                                    value=self.realizations(self.ensembles[0])[0],
                                    id=real_id,
                                    clearable=False,
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=real_prev_id,
                                    children="Prev",
                                ),
                                html.Button(
                                    style={
                                        "fontSize": "1rem",
                                        "padding": "10px",
                                        "textTransform": "none",
                                    },
                                    id=real_next_id,
                                    children="Next",
                                ),
                            ],
                        ),
                    ]
                ),
            ]
        )

    @property
    def layout(self):
        return html.Div(
            [
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                self.selector.layout,
                                self.ensemble_layout(
                                    ensemble_id=self.uuid("ensemble"),
                                    ens_prev_id=self.uuid("ensemble-prev"),
                                    ens_next_id=self.uuid("ensemble-next"),
                                    real_id=self.uuid("realization"),
                                    real_prev_id=self.uuid("realization-prev"),
                                    real_next_id=self.uuid("realization-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                self.selector2.layout,
                                self.ensemble_layout(
                                    ensemble_id=self.uuid("ensemble2"),
                                    ens_prev_id=self.uuid("ensemble2-prev"),
                                    ens_next_id=self.uuid("ensemble2-next"),
                                    real_id=self.uuid("realization2"),
                                    real_prev_id=self.uuid("realization2-prev"),
                                    real_next_id=self.uuid("realization2-next"),
                                ),
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
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
                            ],
                        ),
                    ],
                ),
                wcc.FlexBox(
                    style={"fontSize": "1rem"},
                    children=[
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map2"), self.uuid("map3")],
                                    id=self.uuid("map"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map3")],
                                    id=self.uuid("map2"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                        html.Div(
                            style={"margin": "10px", "flex": 4},
                            children=[
                                LayeredMap(
                                    sync_ids=[self.uuid("map"), self.uuid("map2")],
                                    id=self.uuid("map3"),
                                    height=600,
                                    layers=[],
                                    hillShading=True,
                                )
                            ],
                        ),
                    ],
                ),
            ]
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
                Input(self.uuid("realization2"), "value"),
                Input(self.uuid("calculation"), "value"),
            ],
        )
        def _set_base_layer(data, ensemble, real, data2, ensemble2, real2, calculation):
            if not data or not data2:
                raise PreventUpdate
            if real in ["Mean", "StdDev", "Min", "Max"]:
                surface = calculate_surface(self.get_ens_runpath(data, ensemble), real)

            else:
                surface = xtgeo.RegularSurface(self.get_runpath(data, ensemble, real))
            if real2 in ["Mean", "StdDev", "Min", "Max"]:
                surface2 = calculate_surface(
                    self.get_ens_runpath(data2, ensemble2), real2
                )

            else:
                surface2 = xtgeo.RegularSurface(
                    self.get_runpath(data2, ensemble2, real2)
                )

            surface3 = surface.copy()
            try:
                if calculation == "Difference":
                    surface3.values = surface3.values - surface2.values
                if calculation == "Sum":
                    surface3.values = surface3.values + surface2.values
                if calculation == "Product":
                    surface3.values = surface3.values * surface2.values
                if calculation == "Quotient":
                    surface3.values = surface3.values / surface2.values
                layers3 = [
                    make_surface_layer(
                        surface3, name="surface", color="viridis", hillshading=True
                    )
                ]
            except ValueError:
                layers3 = []

            surface_layer = make_surface_layer(
                surface, name="surface", color="viridis", hillshading=True
            )
            surface_layer2 = make_surface_layer(
                surface2, name="surface", color="viridis", hillshading=True
            )

            return [surface_layer], [surface_layer2], layers3

        def _update_from_btn(_n_prev, _n_next, current_value, options):
            """Updates dropdown value if previous/next btn is clicked"""
            options = [opt["value"] for opt in options]
            ctx = dash.callback_context.triggered
            if not ctx or current_value is None:
                raise PreventUpdate
            if not ctx[0]["value"]:
                return current_value
            callback = ctx[0]["prop_id"]
            if "-prev" in callback:
                return prev_value(current_value, options)
            if "next" in callback:
                return next_value(current_value, options)
            return current_value

        for btn_name in ["ensemble", "realization", "ensemble2", "realization2"]:
            app.callback(
                Output(self.uuid(f"{btn_name}"), "value"),
                [
                    Input(self.uuid(f"{btn_name}-prev"), "n_clicks"),
                    Input(self.uuid(f"{btn_name}-next"), "n_clicks"),
                ],
                [
                    State(self.uuid(f"{btn_name}"), "value"),
                    State(self.uuid(f"{btn_name}"), "options"),
                ],
            )(_update_from_btn)

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
                    store_functions.append((get_path, [{"path": str(path)}]))

        # Calculate and store statistics
        for _, ens_df in self.ens_df.groupby("ENSEMBLE"):
            runpaths = list(ens_df["RUNPATH"].unique())
            for filename in filenames:
                paths = [
                    str(Path(runpath) / "share" / "results" / "maps" / filename)
                    for runpath in runpaths
                ]
                for statistic in ["Mean", "StdDev", "Min", "Max"]:
                    store_functions.append(
                        (save_surface, [{"fns": paths, "statistic": statistic}])
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


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface(fns, statistic):
    return surface_from_json(json.load(save_surface(fns, statistic)))


@webvizstore
def save_surface(fns, statistic) -> io.BytesIO:
    surfaces = xtgeo.Surfaces(fns)
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface()
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

    return io.BytesIO(surface_to_json(surface).encode())


def surface_to_json(surface):
    return json.dumps(
        {
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xori": surface.xori,
            "yori": surface.yori,
            "rotation": surface.rotation,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
            "values": surface.values.copy().filled(np.nan).tolist(),
        }
    )


def surface_from_json(surfaceobj):
    return xtgeo.RegularSurface(**surfaceobj)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surfaces(fns):
    return xtgeo.surface.surfaces.Surfaces(fns)


@webvizstore
def get_path(path) -> Path:

    return Path(path)


def prev_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[max(0, index - 1)]
    except ValueError:
        return current_value


def next_value(current_value, options):
    try:
        index = options.index(current_value)
        return options[min(len(options) - 1, index + 1)]

    except ValueError:
        return current_value
