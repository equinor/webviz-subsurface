# pylint: disable=too-many-lines
from typing import List, Dict, Union, Tuple, Callable, Optional
import sys
from pathlib import Path
import json
from datetime import datetime
import time
from fmu import ensemble

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from webviz_config import WebvizPluginABC, EncodedFile
from webviz_config import WebvizSettings
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from webviz_subsurface._models import EnsembleSetModel
from webviz_subsurface._models import caching_ensemble_set_model_factory
from .._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
    historical_vector,
)
from .._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
    get_simulation_line_shape,
    calc_series_statistics,
    add_fanchart_traces,
    add_statistics_traces,
    render_hovertemplate,
    date_to_interval_conversion,
    check_and_format_observations,
)
from .._utils.unique_theming import unique_colors
from .._datainput.from_timeseries_cumulatives import (
    calc_from_cumulatives,
    rename_vec_from_cum,
)


class ProdMisfit(WebvizPluginABC):
    """Visualizes production data misfit at selected date.

    **Features**
    * Visualization of prod misfit at selected time.
    * Visualization of prod coverage at selected time.

    ---
    xxx
    ---
    yyy"""

    ENSEMBLE_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        sampling: Union[str, list] = "yearly",
        # sampling: Union[str, list] = ["2021-07-01", "2021-01-01", "2020-01-01"],
        excl_name_startswith: tuple = ("R_", "RFT_", "DHG_"),
        excl_name_contains: tuple = ("WI", "GI", "INJ"),
        well_file: Optional[Path] = None,
    ):

        t1 = time.time()
        super().__init__()

        self.ensembles = ensembles
        self.time_index = sampling

        t2 = time.time()
        # well_list = _get_wellnames(
        #    self.ensembles,
        #    webviz_settings,
        #    excl_startswith=excl_name_startswith,
        #    excl_contains=excl_name_contains,
        # )
        # print(well_list)
        t3 = time.time()

        # smry_vectors = ["WOPT", "WWPT", "WGPT"]
        # self.column_keys = _get_colkeys(well_list, smry_vectors)
        # print(self.column_keys)

        self.emodel: EnsembleSetModel = caching_ensemble_set_model_factory.get_or_create_model(
            ensemble_paths={
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            },
            time_index=self.time_index,
            # time_index=[datetime.strptime("2020-01-01", "%Y-%m-%d")],
            column_keys=["WOPT:*", "WWPT:*", "WGPT:*"],
        )
        t4 = time.time()
        print(self.emodel)
        # print(self.emodel._ensemble_paths)

        self.df_smry: pd.DataFrame = self.emodel.get_or_load_smry_cached()
        print(self.df_smry)
        t5 = time.time()

        # auto-remove columns/vectors with all zeros
        # self.df_smry = self.df_smry.loc[:, (self.df_smry != 0).any(axis=0)]
        # print(self.df_smry)

        # remove columns if in excl_name_startswith or excl_name_contains
        self.df_smry = _get_filtered_df(
            self.df_smry, excl_name_startswith, excl_name_contains
        )
        print(self.df_smry)
        t6 = time.time()

        # self.df_smry_meta: pd.DataFrame = self.emodel.load_smry_meta()
        # print(self.df_smry_meta)

        # make df of corresponding hist vectors, only need to get from 1 valid real
        ens_for_hist = self.df_smry.ENSEMBLE.values[0]
        real_for_hist = self.df_smry.REAL.values[0]
        path_for_hist = webviz_settings.shared_settings["scratch_ensembles"][
            ens_for_hist
        ].replace("*", str(real_for_hist))

        self.emodel_hist: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={"hist": path_for_hist for ens in ensembles},
                time_index=self.time_index,
                column_keys=["WOPTH:*", "WWPTH:*", "WGPTH:*"],
            )
        )
        self.df_smry_hist: pd.DataFrame = self.emodel_hist.get_or_load_smry_cached()
        self.df_smry_hist = _get_filtered_df(
            self.df_smry_hist, excl_name_startswith, excl_name_contains
        )
        print(self.df_smry_hist)
        t7 = time.time()

        print(t3 - t1)
        print(t4 - t3)
        print(t5 - t4)
        print(t6 - t5)
        print(t7 - t6)

        dframe_diff = _calcualte_diff_at_date(self.df_smry, self.df_smry_hist)
        print(dframe_diff)

        self.set_callbacks(app)

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "55vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Dropdown(
                            label="Ensemble selector",
                            id=self.uuid("ensemble_name"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles,
                            multi=True,
                            clearable=False,
                            persistence=True,
                            persistence_type="memory",
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.uuid("crossplot-graph"), "children"),
        )
        def _update_crossplot_graph(
            # ens_names: List[str],
            # regions: List[Union[int, str]],
            # realizations: List[Union[int, str]],
            # colorby: Optional[str],
            # sizeby: Optional[str],
            # showerrbar: Optional[str],
            # figcols: int,
            # figheight: int,
        ) -> Optional[List[wcc.Graph]]:

            figures = update_crossplot()
            return figures


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)


def _get_wellnames(
    ensembles: list,
    webviz_settings: WebvizSettings,
    excl_startswith: tuple = (),
    excl_contains: tuple = (),
) -> list:
    """
    Return a union of all Eclipse Summary well names.

    This local function is added to handle a deprecation of get_wellname.
    If a better soution comes up, this function should be replaced.

    The well names are extracted from the first realization
    found in ensset that has an OK_FILE in runpath.
    """

    OK_FILE = "OK"
    result = set()

    for ens_name in ensembles:
        path = webviz_settings.shared_settings["scratch_ensembles"][ens_name]
        ensset = ensemble.EnsembleSet("ensset", frompath=path)
        for ens in ensset._ensembles.values():
            for realization in ens.realizations.values():
                print(realization.runpath())
                if realization.contains(OK_FILE):
                    eclsum = realization.get_eclsum()
                    if eclsum:
                        result = result.union(set(eclsum.wells()))
                        break

    well_list = [well for well in list(result) if not well.startswith(excl_startswith)]

    for well in well_list:
        for x in excl_contains:
            if x in well:
                well_list.remove(well)

    return sorted(well_list)


def _get_colkeys(well_list: list, smry_vectors: list) -> list:
    """Read list of wells and return list of corresponding
    smry keys for wopt, wwpt and wgpt)"""

    column_keys: list = []
    for vec in smry_vectors:
        for well in well_list:
            column_keys.append(vec + ":" + well)

    return column_keys


def _get_filtered_df(dframe, excl_name_startswith, excl_name_contains):
    """Remove unwanted wells from dframe"""

    drop_list = []
    for colname in dframe.columns:
        if colname.startswith(excl_name_startswith, 5) or colname.startswith(
            excl_name_startswith, 6
        ):
            drop_list.append(colname)
            continue
        else:
            for excl in excl_name_contains:
                if excl in colname:
                    drop_list.append(colname)
                    continue
    if len(drop_list) > 0:
        print("Dropping column keys: ", drop_list)
    return dframe.drop(columns=drop_list)


def _calcualte_diff_at_date(df_sim, df_hist):
    """calculate diff"""

    date = df_sim.DATE.values[2]
    dframe = pd.DataFrame()
    df_sim = df_sim[df_sim.DATE == date]
    df_hist = df_hist[df_hist.DATE == date]
    for col in df_sim.columns:
        if col in ["REAL", "ENSEMBLE", "DATE"]:
            dframe[col] = df_sim[col]
        elif col.startswith(("WOPT", "WWPT", "WGPT")):
            vector, well = col.split(":")[0], col.split(":")[1]
            print(vector, well)
            dframe[vector + "_DIFF:" + well] = (
                df_sim[col] - df_hist[vector + "H:" + well].values[0]
            )

    return dframe

# -------------------------------
def update_crossplot(df_sim, df_hist, vectortype="WOPT"):

    dframe = pd.DataFrame()
    my_wells = []

    date = df_sim.DATE.values[2]
    df_sim = df_sim[df_sim.DATE == date]
    df_hist = df_hist[df_hist.DATE == date]

    for col in df_sim.columns:
        if col.startswith(vectortype):
            my_wells.append(col.split(":")[1])
            hist[my_wells] = df_hist[vectortype + "H:" + well].values[0]

    hist = {}
    for well in sorted(my_wells):
        hist.append(df_hist[vectortype + "H:" + well].values[0])
        
            

            
    ID = df_hist.columns
    values = df_sim.columns
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
