# pylint: disable=too-many-lines, too-many-arguments, too-many-locals
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import logging
import re
import glob

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash.exceptions import PreventUpdate
from dash import html, dcc, Input, Output
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class SeismicMisfit(WebvizPluginABC):
    """Seismic misfit plotting.
    Consists of several tabs with different plots of
    observed and simulated seismic 4d attribute.
    * Seismic obs data (overview)
    * Seismic misfit per real (misfit quantification and ranking)
    * Seismic crossplot - sim vs obs (data points statistics)
    * Seismic errorbar plot - sim vs obs (data points statistics)
    * Seismic map plot - sim vs obs (data points statistics)

    ---

    * **`myensembles`:** Which *scratch_ensembles* in *shared_settings* to include.
    <br>(Note that **realization-** should be part of the paths.)

    * **`attribute_name_sim`:** Name of simulated seismic attribute

    * **`attribute_name_obs`:** Name of observed seismic attribute.
    If defaulted, it will be set equal to `attribute_name_sim`.

    * **`metadata_name`:** Name of meta data file.
    Must have east, north and region columns for full utilization of plugin.

    * **`attribute_sim_path`:** Path to `attribute_name_sim` file.
    Path is given as relative to *runpath*.<br>
    *runpath* = path as defined for `myensembles` in shared settings.

    * **`attribute_obs_path`:** Path to `attribute_name_obs` file.
    Path is given as relative to *runpath*,

    * **`metadata_path`:** Path to `metadata_name` file.
    Path is given as relative to *runpath*,

    * **`obs_mult`:** Multiplier for all observation and observation error data.
    Can be used for calibration purposes.

    * **`sim_mult`:** Multiplier for all simulated data.
    Can be used for calibration purposes.

    * **`polygon`:** Full path to csv file containing (fault-) polygons
    to include in map view plots.

    * **`realrange`:** Realization range filter for each of the ensembles.
    Assign as list of two integers (e.g. [0, 99]).
    Realizations outside range will be excluded.
    If `realrange` is omitted, no realization filter will be applied (include all).

    ---

    The input data consists of 3 different file types.<br>
    1) Observation data file - `attribute_name_obs`: This is a 2 column file,
    where the columns are space seperated (ERT compatible format).
    First column is the observed attribute value and the second column
    is the corresponding error. This file has no header.<br>
    ```
        0.002072 0.001
        0.001379 0.001
        0.001239 0.001
        ...
        ...
    ```
    2) Simulation data file (one per realization) - `attribute_name_sim`:
    This is a 1 column file (ERT compatible format).
    The column is the simulated attribute value. This file has no header.
    ```
        0.0023456
        0.0012345
        0.0013579
        ...
        ...
    ```
    3) Metadata file - `metadata_name`: This file must include the
    column headers "east" (or x_utme), "north" (or y_utmn) and "region"
    (case insensitive). The columns are comma seperated.
    The file can have more columns, but those will be ignored.<br>
    ```csv
        X_UTME,Y_UTMN,Region
        456166.26,5935963.72,1.0
        456241.17,5935834.17,1.0
        456316.08,5935704.57,1.0
        ...
        ...
    ```

    It is a requirement that each line of data in these 3 files represent
    the same data point. I.e. line number N+1 in `metadata_name` corresponds to
    line N in `attribute_name_obs` and `attribute_name_sim` files.
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        myensembles: List[str],
        attribute_name_sim: str,
        attribute_name_obs: str = None,
        metadata_name: str = "metadata.csv",
        attribute_sim_path: Path = Path(
            "sim2seis/output/4d_attribute_maps/"
        ),  # path relative to <runpath>
        attribute_obs_path: Path = Path(
            "../../share/observations/seismic/"
        ),  # path relative to <runpath>
        metadata_path: Path = Path(
            "../../share/observations/seismic/"
        ),  # path relative to <runpath>
        obs_mult: float = 1.0,
        sim_mult: float = 1.0,
        polygon: Path = None,
        realrange: List[List[int]] = None,
    ):
        super().__init__()

        ensemble_set = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in myensembles
        }
        # self.emodel: EnsembleSetModel = (
        #    caching_ensemble_set_model_factory.get_or_create_model(
        #        ensemble_paths=ensemble_set,
        #    )
        # )

        self.caseinfo = ""
        self.ens_names = []
        for ens_name, ens_path in ensemble_set.items():
            self.caseinfo = self.caseinfo + ens_name + ": \n"
            self.caseinfo = self.caseinfo + ens_path + "\n"
            self.ens_names.append(ens_name)

        if attribute_name_obs is None:
            attribute_name_obs = attribute_name_sim

        # make one dataframe with all data and one with only obs/meta data
        self.dframe, self.dframeobs = makedf(
            ensemble_set,
            attribute_name_sim,
            attribute_name_obs,
            metadata_name,
            attribute_sim_path,
            attribute_obs_path,
            metadata_path,
            obs_mult,
            sim_mult,
            realrange,
        )
        self.obsinfo = _compare_dfs_obs(self.dframeobs, self.ens_names)
        self.caseinfo = self.caseinfo + self.obsinfo

        self.df_polygon = read_csv(polygon) if polygon else None

        # get sorted list of unique region values
        self.region_names = sorted(list(self.dframe["region"].unique()))

        # get list of all realizations in dataframe (based on column names real-x)
        self.realizations = [
            col.replace("real-", "") for col in self.dframe if col.startswith("real")
        ]

        # -- get obs data range
        self.obs_range = [self.dframeobs["obs"].min(), self.dframeobs["obs"].max()]
        self.obs_error_range = [
            self.dframeobs["obs_error"].min(),
            self.dframeobs["obs_error"].max(),
        ]

        # -- get map east/north ranges
        self.map_x_range = [self.dframeobs["east"].min(), self.dframeobs["east"].max()]
        self.map_y_range = [
            self.dframeobs["north"].min(),
            self.dframeobs["north"].max(),
        ]

        self.set_callbacks(app)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("obsdata-ens_name"),
                "content": ("Select ensemble to view."),
            },
            {
                "id": self.uuid("obsdata-regions"),
                "content": ("Region filter. "),
            },
            {
                "id": self.uuid("obsdata-noise_filter"),
                "content": ("Noise filter. In steps of half of the lowest obs error."),
            },
            {
                "id": self.uuid("obsdata-showerror"),
                "content": ("Toggle observation error on or off."),
            },
            {
                "id": self.uuid("obsdata-showhistogram"),
                "content": ("Toggle observation data histogram on or off."),
            },
            {
                "id": self.uuid("obsdata-resetindex"),
                "content": (
                    "Use original ordering (as from imported data) or reset index"
                    + " (can be useful in combination with filters."
                ),
            },
            {
                "id": self.uuid("obsdata-obsmap_colorby"),
                "content": ("Select data to use for coloring of the map view plot."),
            },
            {
                "id": self.uuid("obsdata-obsmap_scale_col_range"),
                "content": (
                    "Select color range scaling factor used "
                    + "with the map view plot."
                ),
            },
            {
                "id": self.uuid("obsdata-graph-raw"),
                "content": ("Observation data 'raw' plot."),
            },
            {
                "id": self.uuid("obsdata-graph-map"),
                "content": ("Observation data map view plot."),
            },
            {
                "id": self.uuid("obsdata-info"),
                "content": (
                    "Info of the ensembles observation data comparison. "
                    + "For a direct comparison they should have the same "
                    + "observation and observation error data."
                ),
            },
            # {
            #    "id": self.uuid(""),
            #    "content": ("."),
            # },
        ]

    def _obs_data_layout(self) -> list:
        children = [
            wcc.FlexBox(
                id=self.uuid("obsdata-layout"),
                children=[
                    wcc.Frame(
                        style={
                            "flex": 1,
                            # "height": "55vh",
                            "maxWidth": "200px",
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble selector",
                                id=self.uuid("obsdata-ens_name"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in self.ens_names
                                ],
                                value=self.ens_names[0],
                                clearable=False,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.SelectWithLabel(
                                label="Region selector",
                                id=self.uuid("obsdata-regions"),
                                options=[
                                    {"label": regno, "value": regno}
                                    for regno in self.region_names
                                ],
                                size=min([len(self.region_names), 5]),
                                value=self.region_names,
                            ),
                            wcc.Slider(
                                label="Noise filter",
                                id=self.uuid("obsdata-noise_filter"),
                                min=0,
                                max=0.5
                                * max(
                                    abs(self.obs_range[0]),
                                    abs(self.obs_range[1]),
                                ),
                                step=0.5 * self.obs_error_range[0],
                                value=0,
                            ),
                            html.Div(
                                id=self.uuid("obsdata-noise_filter_text"),
                                style={
                                    "color": "blue",
                                    "font-size": "15px",
                                },
                            ),
                            wcc.Selectors(
                                label="Raw plot settings",
                                children=[
                                    wcc.RadioItems(
                                        id=self.uuid("obsdata-showerror"),
                                        label="Obs error",
                                        options=[
                                            {
                                                "label": "On",
                                                "value": True,
                                            },
                                            {
                                                "label": "Off",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                    wcc.RadioItems(
                                        id=self.uuid("obsdata-showhistogram"),
                                        label="Histogram",
                                        options=[
                                            {
                                                "label": "On",
                                                "value": True,
                                            },
                                            {
                                                "label": "Off",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                    wcc.RadioItems(
                                        id=self.uuid("obsdata-resetindex"),
                                        label="X-axis settings",
                                        options=[
                                            {
                                                "label": "Reset index/sort by region",
                                                "value": True,
                                            },
                                            {
                                                "label": "Original ordering",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                ],
                            ),
                            wcc.Selectors(
                                label="Map plot settings",
                                children=[
                                    wcc.Dropdown(
                                        label="Color by",
                                        id=self.uuid("obsdata-obsmap_colorby"),
                                        options=[
                                            {
                                                "label": "region",
                                                "value": "region",
                                            },
                                            {
                                                "label": "obs",
                                                "value": "obs",
                                            },
                                            {
                                                "label": "obs error",
                                                "value": "obs_error",
                                            },
                                        ],
                                        value="obs",
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Color range scaling",
                                        id=self.uuid("obsdata-obsmap_scale_col_range"),
                                        options=[
                                            {"label": x, "value": x}
                                            for x in [
                                                0.1,
                                                0.2,
                                                0.3,
                                                0.4,
                                                0.5,
                                                0.6,
                                                0.7,
                                                0.8,
                                                0.9,
                                                1.0,
                                            ]
                                        ],
                                        style={"display": "block"},
                                        value=0.6,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    wcc.Frame(
                        style={"flex": 5, "minWidth": 500},
                        children=[
                            dcc.Graph(
                                id=self.uuid("obsdata-graph-raw"),
                                style={"height": "37vh"},
                            ),
                            dcc.Graph(
                                id=self.uuid("obsdata-graph-map"),
                                style={"height": "52vh"},
                            ),
                            wcc.Selectors(
                                label="Obsdata info",
                                children=[
                                    dcc.Textarea(
                                        id=self.uuid("obsdata-info"),
                                        value=self.obsinfo,
                                        style={
                                            "width": 500,
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
        return children

    def _misfit_per_real_layout(self) -> list:
        children = [
            wcc.FlexBox(
                id=self.uuid("misfit-layout"),
                children=[
                    wcc.Frame(
                        style={
                            "flex": 1,
                            "maxWidth": "200px",
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble selector",
                                id=self.uuid("misfit-ens_names"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in self.ens_names
                                ],
                                value=self.ens_names,
                                multi=True,
                                clearable=False,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.SelectWithLabel(
                                label="Region selector",
                                id=self.uuid("misfit-region"),
                                options=[
                                    {"label": regno, "value": regno}
                                    for regno in self.region_names
                                ],
                                value=self.region_names,
                                size=min([len(self.region_names), 5]),
                            ),
                            wcc.SelectWithLabel(
                                label="Realization selector",
                                id=self.uuid("misfit-realization"),
                                options=[
                                    {"label": real, "value": real}
                                    for real in self.realizations
                                ],
                                value=self.realizations,
                                size=min([len(self.realizations), 5]),
                            ),
                            wcc.Selectors(
                                label="Plot settings and layout",
                                children=[
                                    wcc.Dropdown(
                                        label="Sorting/ranking",
                                        id=self.uuid("misfit-sorting"),
                                        options=[
                                            {
                                                "label": "none",
                                                "value": None,
                                            },
                                            {
                                                "label": "ascending",
                                                "value": True,
                                            },
                                            {
                                                "label": "descending",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                    wcc.Dropdown(
                                        label="Fig layout - height",
                                        id=self.uuid("misfit-figheight"),
                                        options=[
                                            {
                                                "label": "Very small",
                                                "value": 250,
                                            },
                                            {
                                                "label": "Small",
                                                "value": 350,
                                            },
                                            {
                                                "label": "Medium",
                                                "value": 450,
                                            },
                                            {
                                                "label": "Large",
                                                "value": 700,
                                            },
                                            {
                                                "label": "Very large",
                                                "value": 1000,
                                            },
                                        ],
                                        value=350,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                            wcc.Selectors(
                                label="Misfit options",
                                children=[
                                    wcc.Dropdown(
                                        label="Misfit weight",
                                        id=self.uuid("misfit-weight"),
                                        options=[
                                            {
                                                "label": "none",
                                                "value": None,
                                            },
                                            {
                                                "label": "Obs error",
                                                "value": "obs_error",
                                            },
                                        ],
                                        value="obs_error",
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Misfit exponent",
                                        id=self.uuid("misfit-exponent"),
                                        options=[
                                            {
                                                "label": "Linear sum",
                                                "value": 1.0,
                                            },
                                            {
                                                "label": "Squared sum",
                                                "value": 2.0,
                                            },
                                        ],
                                        value=2.0,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Misfit normalization",
                                        id=self.uuid("misfit-normalization"),
                                        options=[
                                            {
                                                "label": "Yes",
                                                "value": True,
                                            },
                                            {
                                                "label": "No",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    wcc.Frame(
                        style={
                            "flex": 5,
                            "minWidth": "500px",
                        },
                        children=[
                            html.Div(id=self.uuid("misfit-graph")),
                            wcc.Selectors(
                                label="Ensemble info",
                                children=[
                                    dcc.Textarea(
                                        id=self.uuid("misfit-ensemble_info"),
                                        value=self.caseinfo,
                                        style={
                                            "width": "500px",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
        return children

    def _crossplot_layout(self) -> list:
        children = [
            wcc.FlexBox(
                id=self.uuid("crossplot-layout"),
                children=[
                    wcc.Frame(
                        style={
                            "flex": 1,
                            "maxWidth": "200px",
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble selector",
                                id=self.uuid("crossplot-ens_names"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in self.ens_names
                                ],
                                value=self.ens_names,
                                multi=True,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.SelectWithLabel(
                                label="Region selector",
                                id=self.uuid("crossplot-region"),
                                options=[
                                    {"label": regno, "value": regno}
                                    for regno in self.region_names
                                ],
                                value=self.region_names,
                            ),
                            wcc.SelectWithLabel(
                                label="Realization selector",
                                id=self.uuid("crossplot-realization"),
                                options=[
                                    {"label": real, "value": real}
                                    for real in self.realizations
                                ],
                                value=self.realizations,
                                size=min([len(self.realizations), 5]),
                            ),
                            wcc.Dropdown(
                                label="Color by",
                                id=self.uuid("crossplot-colorby"),
                                options=[
                                    {
                                        "label": "none",
                                        "value": None,
                                    },
                                    {
                                        "label": "region",
                                        "value": "region",
                                    },
                                ],
                                value="region",
                                clearable=True,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.Dropdown(
                                label="Size by",
                                id=self.uuid("crossplot-sizeby"),
                                options=[
                                    {
                                        "label": "none",
                                        "value": None,
                                    },
                                    {
                                        "label": "sim_std",
                                        "value": "sim_std",
                                    },
                                    {
                                        "label": "diff_mean",
                                        "value": "diff_mean",
                                    },
                                    {
                                        "label": "diff_std",
                                        "value": "diff_std",
                                    },
                                ],
                                value=None,
                            ),
                            wcc.Dropdown(
                                label="Sim errorbar",
                                id=self.uuid("crossplot-showerrorbar"),
                                options=[
                                    {
                                        "label": "None",
                                        "value": None,
                                    },
                                    {
                                        "label": "Sim std",
                                        "value": "sim_std",
                                    },
                                    {
                                        "label": "Sim p10/p90",
                                        "value": "sim_p10_p90",
                                    },
                                ],
                                value="None",
                            ),
                            wcc.Selectors(
                                label="Plot settings and layout",
                                children=[
                                    wcc.Dropdown(
                                        label="Fig layout - height",
                                        id=self.uuid("crossplot-figheight"),
                                        options=[
                                            {
                                                "label": "Very small",
                                                "value": 250,
                                            },
                                            {
                                                "label": "Small",
                                                "value": 350,
                                            },
                                            {
                                                "label": "Medium",
                                                "value": 450,
                                            },
                                            {
                                                "label": "Large",
                                                "value": 700,
                                            },
                                            {
                                                "label": "Very large",
                                                "value": 1000,
                                            },
                                        ],
                                        value=350,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Fig layout - # columns",
                                        id=self.uuid("crossplot-figcolumns"),
                                        options=[
                                            {
                                                "label": "One column",
                                                "value": 1,
                                            },
                                            {
                                                "label": "Two columns",
                                                "value": 2,
                                            },
                                            {
                                                "label": "Three columns",
                                                "value": 3,
                                            },
                                        ],
                                        style={"display": "block"},
                                        value=1,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    wcc.Frame(
                        style={
                            "flex": 4,
                            # "height": "55vh",
                            "minWidth": "500px",
                        },
                        children=[
                            wcc.FlexBox(
                                children=[
                                    html.Div(
                                        # style={"flex": 1},
                                        id=self.uuid("crossplot-graph"),
                                    ),
                                    dcc.Textarea(
                                        id=self.uuid("crossplot-ensembles_info"),
                                        value=self.caseinfo,
                                        style={
                                            "width": "95%",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
        return children

    def _errorbar_plot_layout(self) -> list:
        children = [
            wcc.FlexBox(
                id=self.uuid("errorbarplot-layout"),
                children=[
                    wcc.Frame(
                        style={
                            "flex": 1,
                            "maxWidth": 200,
                            "height": "85vh",
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble selector",
                                id=self.uuid("errorbarplot-ens_names"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in self.ens_names
                                ],
                                value=self.ens_names,
                                multi=True,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.SelectWithLabel(
                                label="Region selector",
                                id=self.uuid("errorbarplot-region"),
                                options=[
                                    {"label": regno, "value": regno}
                                    for regno in self.region_names
                                ],
                                value=self.region_names,
                                size=min([len(self.region_names), 5]),
                            ),
                            wcc.SelectWithLabel(
                                label="Realization selector",
                                id=self.uuid("errorbarplot-realization"),
                                options=[
                                    {"label": real, "value": real}
                                    for real in self.realizations
                                ],
                                value=self.realizations,
                                size=min([len(self.realizations), 5]),
                            ),
                            wcc.Dropdown(
                                label="Color by",
                                id=self.uuid("errorbarplot-colorby"),
                                options=[
                                    {
                                        "label": "none",
                                        "value": None,
                                    },
                                    {
                                        "label": "region",
                                        "value": "region",
                                    },
                                    {
                                        "label": "sim_std",
                                        "value": "sim_std",
                                    },
                                    {
                                        "label": "diff_mean",
                                        "value": "diff_mean",
                                    },
                                    {
                                        "label": "diff_std",
                                        "value": "diff_std",
                                    },
                                ],
                                style={"display": "block"},
                                value="region",
                                clearable=False,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.Dropdown(
                                label="Sim errorbar",
                                id=self.uuid("errorbarplot-showerrorbar"),
                                options=[
                                    {
                                        "label": "Sim std",
                                        "value": "sim_std",
                                    },
                                    {
                                        "label": "Sim p10/p90",
                                        "value": "sim_p10_p90",
                                    },
                                    {
                                        "label": "none",
                                        "value": None,
                                    },
                                ],
                                value="sim_std",
                                clearable=True,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.Dropdown(
                                label="Obs errorbar",
                                id=self.uuid("errorbarplot-showerrorbarobs"),
                                options=[
                                    {
                                        "label": "Obs std",
                                        "value": "obs_error",
                                    },
                                    {
                                        "label": "none",
                                        "value": None,
                                    },
                                ],
                                value=None,
                            ),
                            wcc.Selectors(
                                label="Plot settings and layout",
                                children=[
                                    wcc.Dropdown(
                                        label="X axis settings",
                                        id=self.uuid("errorbarplot-resetindex"),
                                        options=[
                                            {
                                                "label": "Reset index/sort by region",
                                                "value": True,
                                            },
                                            {
                                                "label": "Original ordering",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                    wcc.RadioItems(
                                        label="Superimpose plots",
                                        id=self.uuid("errorbarplot-superimpose"),
                                        options=[
                                            {
                                                "label": "True",
                                                "value": True,
                                            },
                                            {
                                                "label": "False",
                                                "value": False,
                                            },
                                        ],
                                        value=False,
                                    ),
                                    wcc.Dropdown(
                                        label="Fig layout - height",
                                        id=self.uuid("errorbarplot-figheight"),
                                        options=[
                                            {
                                                "label": "Very small",
                                                "value": 250,
                                            },
                                            {
                                                "label": "Small",
                                                "value": 350,
                                            },
                                            {
                                                "label": "Medium",
                                                "value": 450,
                                            },
                                            {
                                                "label": "Large",
                                                "value": 700,
                                            },
                                            {
                                                "label": "Very large",
                                                "value": 1000,
                                            },
                                        ],
                                        value=450,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Fig layout - # columns",
                                        id=self.uuid("errorbarplot-figcolumns"),
                                        options=[
                                            {
                                                "label": "One column",
                                                "value": 1,
                                            },
                                            {
                                                "label": "Two columns",
                                                "value": 2,
                                            },
                                            {
                                                "label": "Three columns",
                                                "value": 3,
                                            },
                                        ],
                                        style={"display": "block"},
                                        value=1,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    wcc.Frame(
                        style={
                            "flex": 4,
                            "minWidth": "500px",
                        },
                        children=[
                            html.Div(
                                id=self.uuid("errorbarplot-graph"),
                            ),
                            wcc.Selectors(
                                label="Ensemble info",
                                children=[
                                    dcc.Textarea(
                                        id=self.uuid("errorbarplot-ensembles_info"),
                                        value=self.caseinfo,
                                        style={
                                            "width": "95%",
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
        return children

    def _map_plot_layout(self) -> list:
        children = [
            wcc.FlexBox(
                id=self.uuid("map_plot-layout"),
                children=[
                    wcc.Frame(
                        style={
                            "flex": 1,
                            "height": "50vh",
                            "maxWidth": "200px",
                        },
                        children=[
                            wcc.Dropdown(
                                label="Ensemble selector",
                                id=self.uuid("map_plot-ens_name"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in self.ens_names
                                ],
                                value=self.ens_names[0],
                                clearable=False,
                                persistence=True,
                                persistence_type="memory",
                            ),
                            wcc.SelectWithLabel(
                                label="Region selector",
                                # className="webviz-select-with-label",
                                id=self.uuid("map_plot-regions"),
                                options=[
                                    {"label": regno, "value": regno}
                                    for regno in self.region_names
                                ],
                                size=min([len(self.region_names), 5]),
                                value=self.region_names,
                            ),
                            wcc.SelectWithLabel(
                                label="Realization selector",
                                id=self.uuid("map_plot-realizations"),
                                options=[
                                    {"label": real, "value": real}
                                    for real in self.realizations
                                ],
                                size=min([len(self.realizations), 5]),
                                value=self.realizations,
                            ),
                            wcc.Selectors(
                                label="Map plot settings",
                                children=[
                                    wcc.Dropdown(
                                        label="Show difference or coverage plot",
                                        id=self.uuid("map_plot-plot_coverage"),
                                        options=[
                                            {
                                                "label": "Difference plot",
                                                "value": 0,
                                            },
                                            {
                                                "label": "Coverage plot",
                                                "value": 1,
                                            },
                                            {
                                                "label": "Coverage plot (obs error adjusted)",
                                                "value": 2,
                                            },
                                        ],
                                        value=0,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Color range scaling - obs and sim",
                                        id=self.uuid("map_plot-scale_col_range"),
                                        options=[
                                            {"label": val, "value": val}
                                            for val in [
                                                0.1,
                                                0.2,
                                                0.3,
                                                0.4,
                                                0.5,
                                                0.6,
                                                0.7,
                                                0.8,
                                                0.9,
                                                1.0,
                                                1.5,
                                                2,
                                                5,
                                                10,
                                            ]
                                        ],
                                        value=0.6,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                    wcc.Dropdown(
                                        label="Marker size",
                                        id=self.uuid("map_plot-marker_size"),
                                        options=[
                                            {"label": val, "value": val}
                                            for val in [
                                                5,
                                                10,
                                                12,
                                                14,
                                                16,
                                                18,
                                                20,
                                                25,
                                                30,
                                            ]
                                        ],
                                        value=12,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                            wcc.Selectors(
                                label="Slice settings",
                                children=[
                                    wcc.Dropdown(
                                        label="Slicing accuracy (north ± meters)",
                                        id=self.uuid("map_plot-slice_accuracy"),
                                        options=[
                                            {"label": "± 10m", "value": 10},
                                            {"label": "± 25m", "value": 25},
                                            {"label": "± 50m", "value": 50},
                                            {"label": "± 75m", "value": 75},
                                            {
                                                "label": "± 100m",
                                                "value": 100,
                                            },
                                            {
                                                "label": "± 150m",
                                                "value": 150,
                                            },
                                            {
                                                "label": "± 200m",
                                                "value": 200,
                                            },
                                            {
                                                "label": "± 250m",
                                                "value": 250,
                                            },
                                        ],
                                        value=75,
                                        clearable=False,
                                        persistence=True,
                                        persistence_type="memory",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    wcc.Frame(
                        # color="lightblue",
                        style={"flex": 4, "minWidth": "900px"},
                        children=[
                            dcc.Graph(
                                id=self.uuid("map_plot-figs"),
                                style={"height": 650},
                            ),
                            html.P("North position of slice"),
                            wcc.Slider(
                                id=self.uuid("map_plot-slice_position"),
                                min=self.map_y_range[0],
                                max=self.map_y_range[1],
                                value=(self.map_y_range[0] + self.map_y_range[1]) / 2,
                                step=100,
                                marks={
                                    str(
                                        self.map_y_range[0]
                                    ): f"min={round(self.map_y_range[0]):,}",
                                    str(
                                        self.map_y_range[1]
                                    ): f"max={round(self.map_y_range[1]):,}",
                                },
                            ),
                            dcc.Graph(
                                id=self.uuid("map_plot-slice"),
                                style={"height": 550},
                            ),
                        ],
                    ),
                ],
            ),
        ]
        return children

    @property
    def layout(self) -> wcc.Tabs:

        tabs_styles = {"height": "60px", "width": "100%"}

        tab_style = {
            "borderBottom": "1px solid #d6d6d6",
            "padding": "6px",
            "fontWeight": "bold",
        }

        tab_selected_style = {
            "borderTop": "1px solid #d6d6d6",
            "borderBottom": "1px solid #d6d6d6",
            "backgroundColor": "#007079",
            "color": "white",
            "padding": "6px",
        }

        return wcc.Tabs(
            style=tabs_styles,
            children=[
                wcc.Tab(
                    label="Seismic obs data",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=self._obs_data_layout(),
                ),
                wcc.Tab(
                    label="Seismic misfit per real",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=self._misfit_per_real_layout(),
                ),
                wcc.Tab(
                    label="Seismic crossplot - sim vs obs",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=self._crossplot_layout(),
                ),
                wcc.Tab(
                    label="Seismic errorbar plot - sim vs obs",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=self._errorbar_plot_layout(),
                ),
                wcc.Tab(
                    label="Seismic map plot - sim vs obs",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=self._map_plot_layout(),
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: dash.Dash) -> None:

        # --- Seismic obs data ---
        @app.callback(
            Output(self.uuid("obsdata-graph-raw"), "figure"),
            Output(self.uuid("obsdata-graph-map"), "figure"),
            Output(self.uuid("obsdata-obsmap_scale_col_range"), "style"),
            Output(self.uuid("obsdata-noise_filter_text"), "children"),
            Input(self.uuid("obsdata-ens_name"), "value"),
            Input(self.uuid("obsdata-regions"), "value"),
            Input(self.uuid("obsdata-noise_filter"), "value"),
            Input(self.uuid("obsdata-showerror"), "value"),
            Input(self.uuid("obsdata-showhistogram"), "value"),
            Input(self.uuid("obsdata-resetindex"), "value"),
            Input(self.uuid("obsdata-obsmap_colorby"), "value"),
            Input(self.uuid("obsdata-obsmap_scale_col_range"), "value"),
            # prevent_initial_call=True,
        )
        def _update_obsdata_graph(
            ens_name: str,
            regions: List[Union[int, str]],
            noise_filter: float,
            showerror: bool,
            showhistogram: bool,
            resetindex: bool,
            obsmap_colorby: str,
            obsmap_scale_col_range: float,
        ) -> Tuple[px.scatter, px.scatter, dict, str]:

            if not regions:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]

            # --- apply region filter
            dframe_obs = self.dframeobs.loc[self.dframeobs["region"].isin(regions)]

            # --- apply ensemble filter
            dframe_obs = dframe_obs[dframe_obs.ENSEMBLE.eq(ens_name)]

            # --- apply noise filter
            dframe_obs = dframe_obs[abs(dframe_obs.obs).ge(noise_filter)]

            # --- make graphs
            fig_map = update_obsdata_map(
                dframe_obs.copy(),
                x_range=self.map_x_range,
                y_range=self.map_y_range,
                colorby=obsmap_colorby,
                df_polygon=self.df_polygon,
                obs_range=self.obs_range,
                obs_err_range=self.obs_error_range,
                scale_col_range=obsmap_scale_col_range,
            )
            # if fig_raw is run before fig_map some strange value error
            # my arise at init callback --> unknown reason
            fig_raw = update_obsdata_raw(
                dframe_obs.copy(),
                colorby="region",
                showerror=showerror,
                showhistogram=showhistogram,
                reset_index=resetindex,
                y_range=[
                    self.obs_range[0] - self.obs_error_range[1],
                    self.obs_range[1] + self.obs_error_range[1],
                ],
            )

            show_hide_range_scaling = {"display": "block"}
            if obsmap_colorby == "region":
                show_hide_range_scaling = {"display": "none"}

            noise_filter_text = f"Current noise filter value: {noise_filter}"

            return fig_raw, fig_map, show_hide_range_scaling, noise_filter_text

        # --- Seismic misfit per real ---
        @app.callback(
            Output(self.uuid("misfit-graph"), "children"),
            Input(self.uuid("misfit-ens_names"), "value"),
            Input(self.uuid("misfit-region"), "value"),
            Input(self.uuid("misfit-realization"), "value"),
            Input(self.uuid("misfit-sorting"), "value"),
            Input(self.uuid("misfit-figheight"), "value"),
            Input(self.uuid("misfit-weight"), "value"),
            Input(self.uuid("misfit-exponent"), "value"),
            Input(self.uuid("misfit-normalization"), "value"),
            # prevent_initial_call=True,
        )
        def _update_misfit_graph(
            ens_names: List[str],
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            sorting: str,
            figheight: int,
            misfit_weight: str,
            misfit_exponent: float,
            misfit_normalization: bool,
        ) -> List[wcc.Graph]:

            if not regions:
                raise PreventUpdate
            if not realizations:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]
            realizations = [int(real) for real in realizations]

            # --- apply region filter
            dframe = self.dframe.loc[self.dframe["region"].isin(regions)]

            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs, return as list
            figures = update_misfit_plot(
                dframe,
                sorting,
                figheight,
                misfit_weight,
                misfit_exponent,
                misfit_normalization,
            )
            return figures

        # --- Seismic crossplot - sim vs obs ---
        @app.callback(
            Output(self.uuid("crossplot-graph"), "children"),
            Input(self.uuid("crossplot-ens_names"), "value"),
            Input(self.uuid("crossplot-region"), "value"),
            Input(self.uuid("crossplot-realization"), "value"),
            Input(self.uuid("crossplot-colorby"), "value"),
            Input(self.uuid("crossplot-sizeby"), "value"),
            Input(self.uuid("crossplot-showerrorbar"), "value"),
            Input(self.uuid("crossplot-figcolumns"), "value"),
            Input(self.uuid("crossplot-figheight"), "value"),
            # prevent_initial_call=True,
        )
        def _update_crossplot_graph(
            ens_names: List[str],
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            colorby: Optional[str],
            sizeby: Optional[str],
            showerrbar: Optional[str],
            figcols: int,
            figheight: int,
        ) -> Optional[List[wcc.Graph]]:

            if not regions:
                raise PreventUpdate
            if not realizations:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]
            realizations = [int(real) for real in realizations]

            # --- apply region filter
            dframe = self.dframe.loc[self.dframe["region"].isin(regions)]

            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs
            figures = update_crossplot(
                dframe,
                colorby=colorby,
                sizeby=sizeby,
                showerrorbar=showerrbar,
                plot_range=[
                    self.obs_range[0] - self.obs_error_range[1],
                    self.obs_range[1] + self.obs_error_range[1],
                ],
                fig_columns=figcols,
                figheight=figheight,
            )
            return figures

        # --- Seismic errorbar plot - sim vs obs ---
        @app.callback(
            Output(self.uuid("errorbarplot-graph"), "children"),
            Output(self.uuid("errorbarplot-figcolumns"), "style"),
            Output(self.uuid("errorbarplot-colorby"), "style"),
            Input(self.uuid("errorbarplot-ens_names"), "value"),
            Input(self.uuid("errorbarplot-region"), "value"),
            Input(self.uuid("errorbarplot-realization"), "value"),
            Input(self.uuid("errorbarplot-colorby"), "value"),
            Input(self.uuid("errorbarplot-showerrorbar"), "value"),
            Input(self.uuid("errorbarplot-showerrorbarobs"), "value"),
            Input(self.uuid("errorbarplot-resetindex"), "value"),
            Input(self.uuid("errorbarplot-superimpose"), "value"),
            Input(self.uuid("errorbarplot-figcolumns"), "value"),
            Input(self.uuid("errorbarplot-figheight"), "value"),
            # prevent_initial_call=True,
        )
        def _update_errorbar_graph(
            ens_names: List[str],
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            colorby: Optional[str],
            errbar: Optional[str],
            errbarobs: Optional[str],
            resetindex: bool,
            superimpose: bool,
            figcols: int,
            figheight: int,
        ) -> Tuple[Optional[List[wcc.Graph]], Dict[str, str], Dict[str, str]]:

            if not regions:
                raise PreventUpdate
            if not realizations:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]
            realizations = [int(real) for real in realizations]

            # --- apply region filter
            dframe = self.dframe.loc[self.dframe["region"].isin(regions)]
            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            show_hide_selector = {"display": "block"}
            if superimpose:
                show_hide_selector = {"display": "none"}

            # --- apply ensemble filter
            dframe = dframe[dframe.ENSEMBLE.isin(ens_names)]

            # --- make graphs
            if superimpose:
                figures = update_errorbarplot_superimpose(
                    dframe,
                    showerrorbar=errbar,
                    showerrorbarobs=errbarobs,
                    reset_index=resetindex,
                    y_range=[
                        self.obs_range[0] - self.obs_error_range[1],
                        self.obs_range[1] + self.obs_error_range[1],
                    ],
                    figheight=figheight,
                )
            else:
                figures = update_errorbarplot(
                    dframe,
                    colorby=colorby,
                    showerrorbar=errbar,
                    showerrorbarobs=errbarobs,
                    reset_index=resetindex,
                    fig_columns=figcols,
                    y_range=[
                        self.obs_range[0] - self.obs_error_range[1],
                        self.obs_range[1] + self.obs_error_range[1],
                    ],
                    figheight=figheight,
                )
            return figures, show_hide_selector, show_hide_selector

        # --- Seismic map plot - sim vs obs ---
        @app.callback(
            Output(self.uuid("map_plot-figs"), "figure"),
            Output(self.uuid("map_plot-slice"), "figure"),
            Input(self.uuid("map_plot-ens_name"), "value"),
            Input(self.uuid("map_plot-regions"), "value"),
            Input(self.uuid("map_plot-realizations"), "value"),
            Input(self.uuid("map_plot-scale_col_range"), "value"),
            Input(self.uuid("map_plot-slice_accuracy"), "value"),
            Input(self.uuid("map_plot-slice_position"), "value"),
            Input(self.uuid("map_plot-plot_coverage"), "value"),
            Input(self.uuid("map_plot-marker_size"), "value"),
            # prevent_initial_call=True,
        )
        def _update_map_plot_obs_and_sim(
            ens_name: str,
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            scale_col_range: float,
            slice_accuracy: Union[int, float],
            slice_position: float,
            plot_coverage: int,
            marker_size: int,
        ) -> Tuple[Optional[Any], Optional[Any]]:

            if not regions:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]

            # --- apply region filter
            dframe = self.dframe.loc[self.dframe["region"].isin(regions)]

            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            fig_maps, fig_slice = update_obs_sim_map_plot(
                dframe,
                ens_name,
                df_polygon=self.df_polygon,
                x_range=self.map_x_range,
                y_range=self.map_y_range,
                obs_range=self.obs_range,
                scale_col_range=scale_col_range,
                slice_accuracy=slice_accuracy,
                slice_position=slice_position,
                plot_coverage=plot_coverage,
                marker_size=marker_size,
            )

            return fig_maps, fig_slice


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)


# ------------------------------------------------------------------------
# plot, dataframe, support functions, etc below here
# ------------------------------------------------------------------------


# -------------------------------
def update_misfit_plot(
    df: pd.DataFrame,
    sorting: str,
    figheight: int = 450,
    misfit_weight: Optional[str] = None,
    misfit_exponent: float = 1.0,
    normalize: bool = False,
) -> List[wcc.Graph]:
    """Create plot of misfit per realization. One plot per ensemble.
    Misfit is absolute value of |sim - obs|, weighted by obs_error"""

    # max_diff = find_max_diff(df)
    max_diff = None
    min_diff = None
    figures = []

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic misfit plot, updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- calculate absolute diff, (|sim - obs| / obs_error), and store in new df
        ensdf_diff = pd.DataFrame()
        for col in ensdf.columns:
            if col.startswith("real-"):
                ensdf_diff[col] = abs(ensdf[col] - ensdf["obs"])
                if misfit_weight == "obs_error":
                    ensdf_diff[col] = ensdf_diff[col] / ensdf["obs_error"]
                ensdf_diff[col] = ensdf_diff[col] ** misfit_exponent

        # --- make sum of abs diff values over each column (realization)
        ensdf_diff_sum = ensdf_diff.abs().sum().reset_index()
        ensdf_diff_sum = ensdf_diff_sum.rename(columns={"index": "REAL", 0: "ABSDIFF"})
        ensdf_diff_sum["ENSEMBLE"] = ens_name

        if normalize:
            ensdf_diff_sum["ABSDIFF"] = (
                ensdf_diff_sum["ABSDIFF"] / len(ensdf_diff)
            ) ** (1 / misfit_exponent)

        # --- remove "real-" from REAL column values
        # --- (only keep real number for nicer xaxis label)
        ensdf_diff_sum = ensdf_diff_sum.replace(
            to_replace=r"^real-", value="", regex=True
        )

        # --- calculate max/min from first ensemble, use with color range ---
        if max_diff is None:
            max_diff = ensdf_diff_sum["ABSDIFF"].max()
        if min_diff is None:
            min_diff = ensdf_diff_sum["ABSDIFF"].min()

        mean_diff = ensdf_diff_sum["ABSDIFF"].mean()

        # --- sorting ----
        if sorting is not None:
            ensdf_diff_sum = ensdf_diff_sum.sort_values(
                by=["ABSDIFF"], ascending=sorting
            )

        fig = px.bar(
            ensdf_diff_sum,
            x="REAL",
            y="ABSDIFF",
            title=ens_name,
            range_y=[min_diff * 0.30, max_diff * 1.05],
            color="ABSDIFF",
            range_color=[min_diff * 0.30, max_diff * 1.00],
            color_continuous_scale=px.colors.sequential.amp,
        )
        fig.update_xaxes(title_text="Realization")
        fig.update_yaxes(title_text="Cumulative misfit")
        fig.add_hline(mean_diff)
        fig.add_annotation(average_arrow_annotation(mean_diff, "y"))
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig.update_layout(coloraxis_colorbar_thickness=20)
        # fig.update(layout_coloraxis_showscale=False)

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

    return figures


# -------------------------------
def update_obsdata_raw(
    df_obs: pd.DataFrame,
    colorby: Optional[str] = None,
    showerror: bool = False,
    showhistogram: bool = False,
    reset_index: bool = False,
    y_range: Optional[List[float]] = None,
) -> px.scatter:
    """Plot seismic obsdata; raw plot.
    Takes dataframe with obsdata and metadata as input"""

    if colorby not in df_obs.columns and colorby is not None:
        colorby = None
        logging.warning(f"{colorby} is not included, colorby is reset to None")

    df_obs = df_obs.sort_values(by=["region"])
    df_obs = df_obs.astype({colorby: "string"})
    # df_obs = df_obs.astype({colorby: int})

    # ----------------------------------------
    # fig: raw data plot
    # ----------------------------------------

    if reset_index:
        df_obs.reset_index(inplace=True)
        df_obs["data_point"] = df_obs.index + 1
    else:
        df_obs["data_point"] = df_obs.data_number

    marg_y = None
    if showhistogram:
        marg_y = "histogram"

    err_y = None
    if showerror:
        err_y = "obs_error"

    fig_raw = px.scatter(
        df_obs,
        x="data_point",
        y="obs",
        range_y=y_range,
        color=colorby,
        marginal_y=marg_y,
        error_y=err_y,
        hover_data=list(df_obs.columns),
        title="obs data raw plot | colorby: " + str(colorby),
    )
    if reset_index:
        fig_raw.update_xaxes(title_text="data point (sorted by region)")
    else:
        fig_raw.update_xaxes(title_text="data point (original ordering)")
    if showerror:
        fig_raw.update_yaxes(title_text="observation value w/error")
    else:
        fig_raw.update_yaxes(title_text="observation value")

    return fig_raw


# -------------------------------
# pylint: disable=broad-except, dangerous-default-value
def update_obsdata_map(
    df_obs: pd.DataFrame,
    x_range: Optional[List[float]] = None,
    y_range: Optional[List[float]] = None,
    colorby: Optional[str] = None,
    df_polygon: Optional[pd.DataFrame] = None,
    obs_range: List[float] = [-999, 999],
    obs_err_range: List[float] = [-999, 999],
    scale_col_range: float = 0.6,
) -> Optional[px.scatter]:
    """Plot seismic obsdata; map view plot.
    Takes dataframe with obsdata and metadata as input"""

    if ("east" not in df_obs.columns) or ("north" not in df_obs.columns):
        logging.warning("-- Do not have necessary data for making map view plot")
        logging.warning("-- Consider adding east/north coordinates to metafile")
        return None

    if colorby not in df_obs.columns and colorby is not None:
        colorby = None
        logging.warning(f"{colorby} is not included, colorby is reset to None")

    if df_obs[colorby].dtype == "int64" or colorby == "region":
        df_obs = df_obs.sort_values(by=[colorby])
        df_obs = df_obs.astype(
            {colorby: "string"}
        )  # define as string to colorby discrete variable

    # ----------------------------------------
    color_scale = None
    scale_midpoint = None
    range_col = None

    if colorby in ("obs", "obs_error"):
        range_col, scale_midpoint, color_scale = _get_obsdata_col_settings(
            colorby, obs_range, obs_err_range, scale_col_range
        )

    # ----------------------------------------
    # fig, map view plot
    fig = px.scatter(
        df_obs,
        x="east",
        y="north",
        range_x=x_range,
        range_y=y_range,
        color=colorby,
        hover_data=list(df_obs.columns),
        color_continuous_scale=color_scale,
        color_continuous_midpoint=scale_midpoint,
        range_color=range_col,
        title="obs data map view plot | colorby: " + str(colorby),
    )

    # ----------------------------------------
    # add polygon to map if defined
    if df_polygon is not None:
        try:
            for _poly, polydf in df_polygon.groupby("POLY_ID"):
                poly_id = "pol" + str(_poly)
                fig.add_trace(
                    go.Scattergl(
                        x=polydf["X_UTME"],
                        y=polydf["Y_UTMN"],
                        mode="lines",
                        line_color="gray",
                        name=poly_id,
                        showlegend=False,
                    ),
                    row="all",
                    col="all",
                    exclude_empty_subplots=True,
                )
        except Exception as exception:
            logging.warning(f"Failed to add polygon -- {exception}")

    fig.update_yaxes(scaleanchor="x")
    fig.update_layout(coloraxis_colorbar_x=0.95)
    fig.update_layout(coloraxis_colorbar_y=1.0)
    fig.update_layout(coloraxis_colorbar_yanchor="top")
    fig.update_layout(coloraxis_colorbar_len=0.9)
    fig.update_layout(coloraxis_colorbar_thickness=20)
    fig.update_traces(marker=dict(size=12), selector=dict(mode="markers"))

    return fig


# -------------------------------
# pylint: disable=broad-except, dangerous-default-value
def update_obs_sim_map_plot(
    df: pd.DataFrame,
    ens_name: str,
    df_polygon: Optional[pd.DataFrame] = None,
    x_range: Optional[List[float]] = None,
    y_range: Optional[List[float]] = None,
    obs_range: List[float] = [-999, 999],
    scale_col_range: float = 0.6,
    slice_accuracy: Union[int, float] = 100,
    slice_position: float = 0.0,
    plot_coverage: int = 0,
    marker_size: int = 14,
) -> Tuple[Optional[Any], Optional[Any]]:
    """Plot seismic obsdata, simdata and diffdata; side by side map view plots.
    Takes dataframe with obsdata, metadata and simdata as input"""

    logging.debug(f"Seismic obs vs sim map plot, updating {ens_name}")

    ensdf = df[df.ENSEMBLE.eq(ens_name)]

    if ("east" not in ensdf.columns) or ("north" not in ensdf.columns):
        logging.warning("-- Do not have necessary data for making map view plot")
        logging.warning("-- Consider adding east/north coordinates to metafile")
        return None, None

    # --- drop columns (realizations) with no data
    ensdf = ensdf.dropna(axis="columns")

    # --- get dataframe with statistics per datapoint
    ensdf_stat = df_seis_ens_stat(ensdf, ens_name)

    if ensdf_stat.empty:
        return (
            make_subplots(
                rows=1,
                cols=3,
                subplot_titles=("No data for current selection", "---", "---"),
            ),
            go.Figure(),
        )

    # ----------------------------------------
    # set color scale and ranges
    color_scale, lower, upper = None, obs_range[0], obs_range[1]

    if lower >= 0.0:
        upper = max(upper * scale_col_range, lower * 1.01)
        color_scale = px.colors.diverging.Portland
    elif upper <= 0.0:
        lower = min(lower * scale_col_range, upper * 1.01)
        color_scale = px.colors.diverging.Portland
    else:
        col_max = max(abs(lower), upper)
        upper = col_max * scale_col_range
        lower = -1 * upper
        color_scale = px.colors.diverging.balance

    # ----------------------------------------

    title3 = "Coverage plot" if plot_coverage in [1, 2] else "Diff plot"
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("Obs plot", "Sim plot", title3),
        shared_xaxes=True,
        vertical_spacing=0.02,
        shared_yaxes=True,
        horizontal_spacing=0.02,
    )

    fig.add_trace(
        go.Scattergl(
            x=ensdf_stat["east"],
            y=ensdf_stat["north"],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=ensdf["obs"],
                colorscale=color_scale,
                colorbar_x=0.29,
                colorbar_thicknessmode="fraction",
                colorbar_thickness=0.02,
                colorbar_len=0.9,
                cmin=lower,
                cmax=upper,
                showscale=True,
            ),
            showlegend=False,
            hoverinfo="text",
            hovertext=ensdf.obs,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scattergl(
            x=ensdf_stat["east"],
            y=ensdf_stat["north"],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=ensdf_stat["sim_mean"],
                colorscale=color_scale,
                colorbar_x=0.63,
                colorbar_thicknessmode="fraction",
                colorbar_thickness=0.02,
                colorbar_len=0.9,
                cmin=lower,
                cmax=upper,
                showscale=True,
            ),
            showlegend=False,
            hoverinfo="text",
            hovertext=ensdf_stat.sim_mean,
        ),
        row=1,
        col=2,
    )

    if plot_coverage == 0:
        fig.add_trace(
            go.Scattergl(
                x=ensdf_stat["east"],
                y=ensdf_stat["north"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=ensdf_stat["diff_mean"],
                    colorbar_x=0.97,
                    colorbar_thicknessmode="fraction",
                    colorbar_thickness=0.02,
                    colorbar_len=0.9,
                    showscale=True,
                ),
                showlegend=False,
                hoverinfo="text",
                hovertext=ensdf_stat.diff_mean,
            ),
            row=1,
            col=3,
        )
    else:
        coverage = "sim_coverage" if plot_coverage == 1 else "sim_coverage2"
        fig.add_trace(
            go.Scattergl(
                x=ensdf_stat["east"],
                y=ensdf_stat["north"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=ensdf_stat[coverage],
                    cmin=-1.0,
                    cmax=2.0,
                    colorscale=[
                        [0, "blue"],
                        [0.33, "lightblue"],
                        [0.33, "lightgreen"],
                        [0.5, "beige"],
                        [0.67, "lightgreen"],
                        [0.67, "lightcoral"],
                        [1, "red"],
                    ],
                    colorbar=dict(
                        # title="Coverage",
                        tickvals=[-0.5, 0.5, 1.5],
                        ticktext=["Overmodelled", "Coverage", "Undermodelled"],
                    ),
                    colorbar_x=0.97,
                    colorbar_thicknessmode="fraction",
                    colorbar_thickness=0.02,
                    colorbar_len=0.9,
                    showscale=True,
                ),
                opacity=0.5,
                showlegend=False,
                hoverinfo="text",
                hovertext=ensdf_stat[coverage],
            ),
            row=1,
            col=3,
        )

    # ----------------------------------------
    # add horizontal line at slice position
    fig.add_hline(
        y=slice_position,
        line_dash="dot",
        line_color="green",
        row="all",
        col="all",
        annotation_text="slice",
        annotation_position="bottom left",
    )

    # ----------------------------------------
    # add polygon to map if defined
    if df_polygon is not None:
        try:
            for _poly, polydf in df_polygon.groupby("POLY_ID"):
                poly_id = "pol" + str(_poly)
                fig.add_trace(
                    go.Scattergl(
                        x=polydf["X_UTME"],
                        y=polydf["Y_UTMN"],
                        mode="lines",
                        line_color="gray",
                        name=poly_id,
                        showlegend=False,
                    ),
                    row="all",
                    col="all",
                    exclude_empty_subplots=True,
                )
        except Exception as exception:
            logging.warning(f"Failed to add polygon -- {exception}")

    fig.update_xaxes(range=x_range)
    fig.update_yaxes(range=y_range)
    fig.update_yaxes(scaleanchor="x")
    fig.update_xaxes(scaleanchor="x")

    # fig.update_layout(template="plotly_dark")

    # ----------------------------------------
    # Create lineplot along slice

    df_sliced = ensdf_stat[
        (ensdf_stat.north < slice_position + slice_accuracy)
        & (ensdf_stat.north > slice_position - slice_accuracy)
    ]
    df_sliced = df_sliced.sort_values(by="east", ascending=True)

    fig_slice = go.Figure(
        [
            go.Scatter(
                name="Obsdata",
                x=df_sliced["east"],
                y=df_sliced["obs"],
                # mode="markers+lines",
                mode="markers+lines",
                marker=dict(color="red", size=5),
                line=dict(width=2, dash="solid"),
                showlegend=True,
            ),
            go.Scatter(
                name="Sim mean",
                x=df_sliced["east"],
                y=df_sliced["sim_mean"],
                mode="markers+lines",
                marker=dict(color="green", size=3),
                line=dict(width=1, dash="dot"),
                showlegend=True,
            ),
            go.Scatter(
                name="Sim p10",
                x=df_sliced["east"],
                y=df_sliced["sim_p10"],
                mode="lines",
                marker=dict(color="#444"),
                line=dict(width=1),
                showlegend=True,
            ),
            go.Scatter(
                name="Sim p90",
                x=df_sliced["east"],
                y=df_sliced["sim_p90"],
                marker=dict(color="#444"),
                line=dict(width=1),
                mode="lines",
                fillcolor="rgba(68, 68, 68, 0.3)",
                fill="tonexty",
                showlegend=True,
            ),
            go.Scatter(
                name="Sim min",
                x=df_sliced["east"],
                y=df_sliced["sim_min"],
                mode="lines",
                line=dict(width=1, dash="dot", color="grey"),
                showlegend=True,
            ),
            go.Scatter(
                name="Sim max",
                x=df_sliced["east"],
                y=df_sliced["sim_max"],
                mode="lines",
                line=dict(width=1, dash="dot", color="grey"),
                showlegend=True,
            ),
        ]
    )
    fig_slice.update_layout(
        yaxis_title="Attribute value",
        xaxis_title="East",
        title="Attribute values along slice",
        hovermode="x",
    )
    return fig, fig_slice


# -------------------------------
# pylint: disable=too-many-statements
def update_crossplot(
    df: pd.DataFrame,
    colorby: Optional[str] = None,
    sizeby: Optional[str] = None,
    showerrorbar: Optional[str] = None,
    plot_range: Optional[List[float]] = None,
    fig_columns: int = 1,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create crossplot of ensemble average sim versus obs,
    one value per seismic datapoint."""

    first = True
    figures = []
    dfs = []
    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic crossplot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat = df_seis_ens_stat(ensdf, ens_name)
        if ensdf_stat.empty:
            break

        # del ensdf

        if ensdf_stat["sim_std"].isnull().values.any():
            logging.warning(
                "Chosen sizeby is ignored and reset to constant "
                "for current selections (std = nan)."
            )
            sizeby = None

        errory = None
        errory_minus = None
        if showerrorbar == "sim_std":
            errory = "sim_std"
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat["error_plus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p10"]
            )
            ensdf_stat["error_minus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p90"]
            )
            errory = "error_plus"
            errory_minus = "error_minus"

        # -------------------------------------------------------------
        if colorby == "region":
            ensdf_stat = ensdf_stat.sort_values(by=[colorby])
            ensdf_stat = ensdf_stat.astype({"region": "string"})

        # -------------------------------------------------------------
        # get color and zeroline ranges from first case
        if first:
            rmax = max(ensdf_stat["sim_mean"].max(), ensdf_stat["obs"].max())
            rmin = min(ensdf_stat["sim_mean"].min(), ensdf_stat["obs"].min())
            axis_extend = (rmax - rmin) * 0.10
            xplot_range = [rmin - axis_extend, rmax + axis_extend]
            cmin = None
            cmax = None
            if colorby is not None:
                cmin = ensdf_stat[colorby].min()
                if colorby == "region":
                    cmax = ensdf_stat[colorby].max()
                else:
                    cmax = ensdf_stat[colorby].quantile(0.9)
            first = False

        dfs.append(ensdf_stat)
    # -------------------------------------------------------------
    if len(dfs) == 0:
        return None

    df_stat = pd.concat(dfs)

    no_plots = len(df_stat.ENSEMBLE.unique())
    if no_plots <= fig_columns:
        total_height = figheight * (1 + 45 / figheight)
    else:
        total_height = figheight * round(no_plots / fig_columns)

    fig = px.scatter(
        df_stat,
        facet_col="ENSEMBLE",
        facet_col_wrap=fig_columns,
        # height=total_height,
        x="obs",
        y="sim_mean",
        range_x=plot_range,
        range_y=plot_range,
        error_y=errory,
        error_y_minus=errory_minus,
        color=colorby,
        range_color=[cmin, cmax],
        size=sizeby,
        size_max=20,
        hover_data=list(df_stat.columns),
    )
    fig.update_traces(marker=dict(sizemode="area"), error_y_thickness=1.0)

    # add zero/diagonal line
    tracelegend = False
    # if colorby == "region":
    #    tracelegend = True
    fig.add_trace(
        go.Scattergl(
            x=xplot_range,
            y=xplot_range,
            mode="lines",
            line_color="gray",
            name="zeroline",
            showlegend=tracelegend,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )

    # marker line color, default is white
    if sizeby is None:
        fig.update_traces(
            marker=dict(line=dict(width=0.4, color="black")),
            selector=dict(mode="markers"),
        )

    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": total_height}))
    return figures


# -------------------------------
# pylint: disable=too-many-statements
def update_errorbarplot(
    df: pd.DataFrame,
    colorby: Optional[str] = None,
    showerrorbar: Optional[str] = None,
    showerrorbarobs: Optional[str] = None,
    reset_index: bool = False,
    fig_columns: int = 1,
    y_range: Optional[List[float]] = None,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create errorbar plot of ensemble sim versus obs,
    one value per seismic datapoint."""

    first = True
    figures = []
    dfs = []

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic errorbar plot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat = df_seis_ens_stat(ensdf, ens_name)
        if ensdf_stat.empty:
            break

        del ensdf

        errory = None
        errory_minus = None
        if showerrorbar == "sim_std":
            errory = "sim_std"
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat["error_plus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p10"]
            )
            ensdf_stat["error_minus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p90"]
            )
            errory = "error_plus"
            errory_minus = "error_minus"

        # -------------------------------------------------------------
        ensdf_stat = ensdf_stat.sort_values(by=["region"])
        ensdf_stat = ensdf_stat.astype({"region": "string"})

        if reset_index:
            ensdf_stat.reset_index(inplace=True)

        ensdf_stat["counter"] = (
            ensdf_stat.index + 1
        )  # make new counter after reset index

        # -------------------------------------------------------------
        # get color ranges from first case
        if first:
            cmin = None
            cmax = None
            if isinstance(colorby, float):
                cmin = ensdf_stat[colorby].min()
                cmax = ensdf_stat[colorby].quantile(0.8)
            first = False

        dfs.append(ensdf_stat)
    # -------------------------------------------------------------
    if len(dfs) == 0:
        return None

    df_stat = pd.concat(dfs)

    no_plots = len(df_stat.ENSEMBLE.unique())
    if no_plots <= fig_columns:
        total_height = figheight * (1 + 45 / figheight)
    else:
        total_height = figheight * round(no_plots / fig_columns)

    fig = px.scatter(
        df_stat,
        facet_col="ENSEMBLE",
        facet_col_wrap=fig_columns,
        x="counter",
        y="sim_mean",
        range_y=y_range,
        error_y=errory,
        error_y_minus=errory_minus,
        color=colorby,
        range_color=[cmin, cmax],
        hover_data=list(df_stat.columns),
    )
    fig.update_traces(error_y_thickness=1.0, selector=dict(type="scatter"))

    # -----------------------
    obserrory = (
        dict(type="data", array=df_stat["obs_error"], visible=True, thickness=1.0)
        if showerrorbarobs is not None
        else None
    )
    obslegend = colorby == "region"

    fig.add_trace(
        go.Scattergl(
            x=df_stat["counter"],
            y=df_stat["obs"],
            error_y=obserrory,
            mode="markers",
            line_color="gray",
            name="obs",
            showlegend=obslegend,
            opacity=0.5,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )
    fig.update_layout(hovermode="closest")

    if reset_index:
        fig.update_xaxes(title_text="data point (index reset, sorted by region)")
    else:
        fig.update_xaxes(title_text="data point (original numbering)")
    if showerrorbar:
        fig.update_yaxes(title_text="Simulated mean w/error")
    else:
        fig.update_yaxes(title_text="Simulated mean")

    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": total_height}))
    return figures


# -------------------------------
def update_errorbarplot_superimpose(
    df: pd.DataFrame,
    showerrorbar: Optional[str] = None,
    showerrorbarobs: Optional[str] = None,
    reset_index: bool = True,
    y_range: Optional[List[float]] = None,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create errorbar plot of ensemble sim versus obs,
    one value per seismic datapoint."""

    first = True
    figures = []
    ensdf_stat = {}
    data_to_plot = False

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic errorbar plot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat[ens_name] = df_seis_ens_stat(ensdf, ens_name)
        if not ensdf_stat[ens_name].empty:
            data_to_plot = True
        else:
            break

        del ensdf

        # -------------------------------------------------------------
        errory = None

        if showerrorbar == "sim_std":
            errory = dict(
                type="data",
                array=ensdf_stat[ens_name]["sim_std"],
                visible=True,
                thickness=1.0,
            )
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat[ens_name]["error_plus"] = abs(
                ensdf_stat[ens_name]["sim_mean"] - ensdf_stat[ens_name]["sim_p10"]
            )
            ensdf_stat[ens_name]["error_minus"] = abs(
                ensdf_stat[ens_name]["sim_mean"] - ensdf_stat[ens_name]["sim_p90"]
            )
            errory = dict(
                type="data",
                symmetric=False,
                array=ensdf_stat[ens_name]["error_plus"],
                arrayminus=ensdf_stat[ens_name]["error_minus"],
                visible=True,
                thickness=1.0,
            )

        # -------------------------------------------------------------
        ensdf_stat[ens_name] = ensdf_stat[ens_name].sort_values(by=["region"])
        ensdf_stat[ens_name] = ensdf_stat[ens_name].astype({"region": "string"})

        if reset_index:
            ensdf_stat[ens_name].reset_index(inplace=True)

        ensdf_stat[ens_name]["counter"] = (
            ensdf_stat[ens_name].index + 1
        )  # make new counter after index reset

        # -----------------------
        if first:

            fig = px.scatter()

            obserrory = None
            if showerrorbarobs is not None:
                obserrory = dict(
                    type="data",
                    array=ensdf_stat[ens_name]["obs_error"],
                    visible=True,
                    thickness=1.0,
                )

            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["obs"],
                error_y=obserrory,
                mode="markers",
                line_color="gray",
                name="obs",
                showlegend=True,
            )
            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["sim_mean"],
                mode="markers",
                name=ens_name,
                error_y=errory,
            )
            first = False
        # -----------------------
        else:
            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["sim_mean"],
                mode="markers",
                name=ens_name,
                error_y=errory,
            )

    if not data_to_plot:
        return None

    fig.update_layout(hovermode="x")
    fig.update_yaxes(range=y_range)

    if reset_index:
        fig.update_xaxes(title_text="data point (index reset, sorted by region)")
    else:
        fig.update_xaxes(title_text="data point (original numbering)")
    if showerrorbar:
        fig.update_yaxes(title_text="Simulated mean w/error")
    else:
        fig.update_yaxes(title_text="Simulated mean")

    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": figheight}))
    return figures


# -------------------------------
# pylint: disable=broad-except
def makedf(
    ensemble_set: dict,
    attribute_name_sim: str,
    attribute_name_obs: str,
    metadata_name: str,
    attribute_sim_path: Path,
    attribute_obs_path: Path,
    metadata_path: Path,
    obs_mult: float,
    sim_mult: float,
    realrange: Optional[List[List[int]]],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Create dataframe of obs, meta and sim data for all ensembles.
    Uses the functions 'makedf_seis_obs_meta' and 'makedf_seis_addsim'."""

    dfs = []
    dfs_obs = []
    ens_count = 0
    for ens_name, ens_path in ensemble_set.items():
        logging.info(
            f"\nWorking with {ens_name}: {ens_path}"
            f"\nSeismic attribute: {attribute_name_sim}"
        )

        # grab runpath for one realization and locate obs/meta data relative to it
        single_runpath = glob.glob(ens_path)[0]
        obsfile = Path(single_runpath) / attribute_obs_path / attribute_name_obs
        metafile = Path(single_runpath) / metadata_path / metadata_name

        df = makedf_seis_obs_meta(obsfile, metafile, obs_mult=obs_mult)

        df["ENSEMBLE"] = ens_name  # add ENSEBLE column
        dfs_obs.append(df.copy())

        # --- add sim data ---
        fromreal, toreal = 0, 99999
        if realrange is not None:
            try:
                fromreal = int(realrange[ens_count][0])
                toreal = int(realrange[ens_count][1])
            except Exception as exception:
                logging.warning(
                    f"realrange input is assigned wrongly - "
                    f"continuing without real filter. {exception}"
                )

        df = makedf_seis_addsim(
            df,
            ens_path,
            attribute_name_sim,
            attribute_sim_path,
            fromreal=fromreal,
            toreal=toreal,
            sim_mult=sim_mult,
        )
        dfs.append(df)

        ens_count += 1

    return pd.concat(dfs), pd.concat(dfs_obs)


# -------------------------------
def makedf_seis_obs_meta(
    obsfile: Path,
    metafile: Path,
    obs_mult: float = 1.0,
) -> pd.DataFrame:
    """Make a merged dataframe of obsdata and metadata.
    Meta file should have a "region" parameter (case insensitive).
    If not included, a region parameter is created with const value = 1.
    (obs data multiplier: optional, default is 1.0")
    """
    # --- read obsfile into pandas dataframe ---
    dframe = pd.read_csv(obsfile, sep=r"\s+", header=None, names=["obs", "obs_error"])
    tot_nan_val_obs = dframe.isnull().sum().sum()  # count all nan values
    if tot_nan_val_obs > 0:
        logging.warning(f"-- obsfile contains {tot_nan_val_obs} NaN values")

    # pylint: disable=no-member, unsupported-assignment-operation
    # https://github.com/PyCQA/pylint/issues/4577
    dframe["data_number"] = dframe.index + 1  # add a simple counter

    # --- read metadata into pandas dataframe ---
    try:
        df_meta = pd.read_csv(metafile)  # read metafile to dataframe
        df_meta.columns = (
            df_meta.columns.str.lower()
        )  # convert all headers to lower case

        if "east" not in df_meta.columns:
            if "x_utme" in df_meta.columns:
                df_meta.rename(columns={"x_utme": "east"}, inplace=True)
                logging.debug("renamed x_utme column to east")
            else:
                logging.warning("x_utm or east column not included in meta data")

        if "north" not in df_meta.columns:
            if "y_utmn" in df_meta.columns:
                df_meta.rename(columns={"y_utmn": "north"}, inplace=True)
                logging.debug("renamed y_utmn column to north")
            else:
                logging.warning("y_utm or north column not included in meta data")

        tot_nan_val_meta = df_meta.isnull().sum().sum()  # count all nan values
        if tot_nan_val_meta > 0:
            logging.warning(f"-- metafile contains {tot_nan_val_meta} NaN values")
    except IOError as ioe:
        logging.warning("-- Continuing without metadata due to error:")
        logging.warning(ioe)
    # pylint: enable=no-member, unsupported-assignment-operation

    # --- concat obsdata and metadata ---
    try:
        dframe = pd.concat([dframe, df_meta], axis=1, sort=False)
    except Exception as exception:
        logging.warning(exception)
        logging.warning(
            "---WARNING. Failed to merge obsdata and metadata. "
            "Please check consistency or if metadata file exists."
        )
        logging.warning(f"Metadata file: {metafile}")

    # --- apply obs multiplier ---
    dframe["obs"] = dframe["obs"] * obs_mult
    dframe["obs_error"] = dframe["obs_error"] * obs_mult

    # --- add dummy region data if not included ---
    if "region" not in dframe.columns:
        logging.warning(
            "-- region column not included in meta data. "
            "Adding dummy region data with const value = 1"
        )
        dframe["region"] = 1

    # -------------------------------

    # force region column to be of type int (if user exported as float)
    # dframe = dframe.astype({"region": int})

    # -------------------------------
    logging.debug(f"Number of seismic data points: {len(dframe)}")
    logging.debug(
        f"Obs file: {obsfile} \n--> Number of undefined values: {tot_nan_val_obs}"
    )
    logging.debug(
        f"Meta file: {metafile}" f"\n--> Number of undefined values: {tot_nan_val_meta}"
    )

    return dframe


# pylint: disable=broad-except
def makedf_seis_addsim(
    df: pd.DataFrame,
    ens_path: str,
    attribute_name_sim: str,
    attribute_sim_path: Path,
    fromreal: int = 0,
    toreal: int = 99,
    sim_mult: float = 1.0,
) -> pd.DataFrame:
    """Make a merged dataframe of obsdata/metadata and simdata."""

    data_found, no_data_found = [], []
    real_path = {}

    runpaths = glob.glob(ens_path)
    if len(runpaths) == 0:
        logging.warning(f"No realizations was found, wrong input?: {ens_path}")
        return pd.DataFrame()

    for runpath in runpaths:
        realno = int(re.search(r"(?<=realization-)\d+", runpath).group(0))  # type: ignore
        real_path[realno] = runpath

    for real in sorted(real_path.keys()):
        if fromreal <= real <= toreal:

            simfile = (
                Path(real_path[real]) / attribute_sim_path / Path(attribute_name_sim)
            )
            try:
                colname = "real-" + str(real)
                df[colname] = pd.read_csv(simfile, header=None)
                df[colname] = df[colname] * sim_mult  # --- apply sim multiplier ---
                data_found.append(real)
            except Exception as exception:
                no_data_found.append(real)
                logging.debug(exception)
                # logging.debug(f"File does not exist: {str(simfile)}")

    logging.debug(f"Sim values added to dataframe for realizations: {data_found}")
    if len(no_data_found) == 0:
        logging.debug("OK. Found data for all realizations")
    else:
        logging.debug(f"No data found for realizations: {no_data_found}")

    return df


def df_seis_ens_stat(
    df: pd.DataFrame, ens_name: str, obs_error_weight: bool = False
) -> pd.DataFrame:
    """Make a dataframe with ensemble statistics per datapoint across all realizations.
    Calculate for both sim and diff values. Return with obs/meta data included.
    Return empty dataframe if no realizations included in df."""

    # --- make dataframe with obs and meta data only
    column_names = df.columns.values.tolist()
    x = [name for name in column_names if not name.startswith("real-")]
    start, end = x[0], x[-1]
    df_obs_meta = df.loc[:, start:end]

    # --- make dataframe with real- columns only
    column_names = df.columns.values.tolist()
    x = [name for name in column_names if name.startswith("real-")]
    if len(x) > 0:
        start, end = x[0], x[-1]
        df_sim = df.loc[:, start:end]
    else:
        logging.info(f"{ens_name}: no data found for selected realizations.")
        return pd.DataFrame()

    # --- calculate absolute diff, (|sim - obs| / obs_error), and store in new df
    df_diff = pd.DataFrame()
    for col in df.columns:
        if col.startswith("real-"):
            df_diff[col] = abs(df[col] - df["obs"])
            if obs_error_weight:
                df_diff[col] = df_diff[col] / df["obs_error"]  # divide by obs error

    # --- ensemble statistics of sim and diff for each data point ----
    # --- calculate statistics per row (data point)
    sim_mean = df_sim.mean(axis=1)
    sim_std = df_sim.std(axis=1)
    sim_p90 = df_sim.quantile(q=0.1, axis=1)
    sim_p10 = df_sim.quantile(q=0.9, axis=1)
    sim_min = df_sim.min(axis=1)
    sim_max = df_sim.max(axis=1)
    diff_mean = df_diff.mean(axis=1)
    diff_std = df_diff.std(axis=1)

    df_stat = pd.DataFrame(
        data={
            "sim_mean": sim_mean,
            "sim_std": sim_std,
            "sim_p90": sim_p90,
            "sim_p10": sim_p10,
            "sim_min": sim_min,
            "sim_max": sim_max,
            "diff_mean": diff_mean,
            "diff_std": diff_std,
        }
    )

    # --- add obsdata and metadata to the dataframe
    df_stat = pd.concat([df_stat, df_obs_meta], axis=1, sort=False)

    # ----------------------
    # Alternative 1:
    # Create coverage parameter as (obs-min)/(max-min), use (max-obs)/(max-min) if obs<0
    # •	Values between 0 and 1 = coverage
    # •	Values above 1 = all sim values lower than obs values
    # •	Values below 0 = all sim values higher than obs values

    # df_stat["sim_coverage"] = np.where(
    #     df_stat["obs"] < 0,
    #     (df_stat.sim_max - df_stat.obs) / (df_stat.sim_max - df_stat.sim_min),
    #     (df_stat.obs - df_stat.sim_min) / (df_stat.sim_max - df_stat.sim_min),
    # )
    # # include obs_error "damping"
    # df_stat["sim_coverage2"] = np.where(
    #     df_stat["obs"] < 0,
    #     (df_stat.sim_max - df_stat.obs)
    #     / (df_stat.obs_error + df_stat.sim_max - df_stat.sim_min),
    #     (df_stat.obs - df_stat.sim_min)
    #     / (df_stat.obs_error + df_stat.sim_max - df_stat.sim_min),
    # )

    # Alternative 2: (obs-min)/(obs_error+max-min), use same for all obs values
    df_stat["sim_coverage"] = (df_stat.obs - df_stat.sim_min) / (
        df_stat.sim_max - df_stat.sim_min
    )
    df_stat["sim_coverage2"] = (df_stat.obs - df_stat.sim_min) / (
        df_stat.obs_error + df_stat.sim_max - df_stat.sim_min
    )

    # force to zero if diff smaller than obs_error
    # (this removes dilemma of small negative values showing up as overmodelled)
    df_stat["sim_coverage2"] = np.where(
        abs(df_stat.obs - df_stat.sim_min) < df_stat.obs_error,
        0,
        df_stat["sim_coverage2"],
    )
    df_stat["sim_coverage2"] = np.where(
        abs(df_stat.obs - df_stat.sim_max) < df_stat.obs_error,
        0,
        df_stat["sim_coverage2"],
    )

    return df_stat


def _get_obsdata_col_settings(
    colorby: str,
    obs_range: List[float],
    obs_err_range: List[float],
    scale_col: float,
) -> Union[Tuple[List[Any], Union[None, float], Any], Tuple[None, None, None]]:
    """return color scale range for obs or obs_error.
    Make range symetric if values above and below zero.
    Adjust range with scale_col value."""

    scale_midpoint = None
    color_scale = px.colors.diverging.Portland

    if colorby == "obs_error":
        lower = obs_err_range[0]
        upper = max(obs_err_range[1] * scale_col, lower * 1.01)
        range_col = [lower, upper]

    elif colorby == "obs":
        if obs_range[0] >= 0.0:
            lower = obs_range[0]
            upper = max(obs_range[1] * scale_col, lower * 1.01)
        elif obs_range[1] <= 0.0:
            upper = obs_range[1]
            lower = min(obs_range[0] * scale_col, upper * 1.01)
        else:
            abs_max = max(abs(obs_range[0]), abs(obs_range[0]))
            upper = abs_max * scale_col
            lower = -1 * upper
            scale_midpoint = 0.0
            color_scale = px.colors.diverging.balance
        range_col = [lower, upper]
    else:
        return None, None, None

    return range_col, scale_midpoint, color_scale


def _compare_dfs_obs(dframeobs: pd.DataFrame, ensembles: List) -> str:
    """Compare obs and obs_error values for ensembles.
    Return info text if not equal"""

    text = ""
    if len(ensembles) > 1:
        ens1 = ensembles[0]
        obs1 = dframeobs[dframeobs.ENSEMBLE.eq(ens1)].obs
        obserr1 = dframeobs[dframeobs.ENSEMBLE.eq(ens1)].obs_error
        for idx in range(1, len(ensembles)):
            ens = ensembles[idx]
            obs = dframeobs[dframeobs.ENSEMBLE.eq(ens)].obs
            obserr = dframeobs[dframeobs.ENSEMBLE.eq(ens)].obs_error

            if not obs1.equals(obs):
                text = (
                    text + "\n--WARNING-- " + ens + " obs data is different to " + ens1
                )
            else:
                text = text + "\n" + "✅ " + ens + " obs data is equal to " + ens1

            if not obserr1.equals(obserr):
                text = (
                    text
                    + "\n--WARNING-- "
                    + ens
                    + " obs error data is different to "
                    + ens1
                )
            else:
                text = text + "\n" + "✅ " + ens + " obs error data is equal to " + ens1

    return text


def get_unique_column_values(df: pd.DataFrame, colname: str) -> List:
    """return dataframe column values. If no matching colname, return [999].
    Currently unused. Consider removing"""
    if colname in df:
        values = df[colname].unique()
        values = sorted(values)
    else:
        values = [999]
    return values


def find_max_diff(df: pd.DataFrame) -> np.float64:
    max_diff = np.float64(0)
    for _ens, ensdf in df.groupby("ENSEMBLE"):
        realdf = ensdf.groupby("REAL").sum().reset_index()
        max_diff = (
            max_diff if max_diff > realdf["ABSDIFF"].max() else realdf["ABSDIFF"].max()
        )
    return max_diff


def average_line_shape(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    return {
        "type": "line",
        "yref": yref,
        "y0": mean_value,
        "y1": mean_value,
        "xref": "paper",
        "x0": 0,
        "x1": 1,
    }


def average_arrow_annotation(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    decimals = 1
    if mean_value < 0.001:
        decimals = 5
    elif mean_value < 0.01:
        decimals = 4
    elif mean_value < 0.1:
        decimals = 3
    elif mean_value < 10:
        decimals = 2
    return {
        "x": 0.2,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": f"Average: {mean_value:.{decimals}f}",
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }
