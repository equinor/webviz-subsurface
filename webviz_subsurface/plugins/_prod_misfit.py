from typing import List, Dict, Union, Tuple, Callable, Optional
import sys
from pathlib import Path
import json
from datetime import datetime
import time
from fmu import ensemble
import plotly.express as px
import plotly.graph_objs as go

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

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        sampling: Union[str, list] = "yearly",
        excl_name_startswith: tuple = ("R_", "RFT_", "DHG_"),
        excl_name_contains: tuple = ("WI", "GI", "INJ"),
        well_file: Optional[Path] = None,
    ):

        super().__init__()

        self.ensembles = ensembles

        t1 = time.time()

        df_smry = pd.read_csv("~/webviz/smry.csv")
        # !!!!# -----------------------------------------
        # !!!!emodel: EnsembleSetModel = (
        # !!!!    caching_ensemble_set_model_factory.get_or_create_model(
        # !!!!        ensemble_paths={
        # !!!!            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
        # !!!!            for ens in ensembles
        # !!!!        },
        # !!!!        time_index=sampling,
        # !!!!        column_keys=["WOPT*:*", "WWPT*:*", "WGPT*:*"],
        # !!!!    )
        # !!!!)
        # !!!!# print(emodel)
        # !!!!# print(emodel._ensemble_paths)
        # !!!!
        # !!!!# -----------------------------------------
        # !!!!df_smry: pd.DataFrame = emodel.get_or_load_smry_cached()
        # print(df_smry)
        # df_smry.to_csv("~/webviz/smry.csv")

        t2 = time.time()
        print(t2 - t1)

        # -----------------------------------------
        # auto-remove columns/vectors with all zeros
        # df_smry = df_smry.loc[:, (df_smry != 0).any(axis=0)]

        # -----------------------------------------
        # remove columns if in excl_name_startswith or excl_name_contains
        df_smry = _get_filtered_df(df_smry, excl_name_startswith, excl_name_contains)

        # Calculate statistics
        self.df_stat = df_sim_ens_stat(df_smry)
        # print(self.df_stat)

        # get list of dates
        self.dates = sorted(list(self.df_stat.DATE.unique()))

        # get list of wells
        self.wells = sorted(list(self.df_stat.WELL.unique()))

        # get list of phases
        self.phases = ["Oil", "Water", "Gas", "Liquid"]
        vectors = list(self.df_stat.VECTOR.unique())
        print(vectors)
        if "WOPT" not in vectors:
            self.phases.remove("Oil")
        if "WWPT" not in vectors:
            self.phases.remove("Water")
        if "WGPT" not in vectors:
            self.phases.remove("Gas")
        if "WLPT" not in vectors:
            print("Consider adding WLPT and WLPTH to summary output")
            self.phases.remove("Liquid")

        # df_smry_meta: pd.DataFrame = emodel.load_smry_meta()
        # print(df_smry_meta)

        # make df of corresponding hist vectors, only need to get from 1 valid real
        # ens_for_hist = df_smry.ENSEMBLE.values[0]
        # real_for_hist = df_smry.REAL.values[0]
        # path_for_hist = webviz_settings.shared_settings["scratch_ensembles"][
        #    ens_for_hist
        # ].replace("*", str(real_for_hist))
        #
        # emodel_hist: EnsembleSetModel = (
        #    caching_ensemble_set_model_factory.get_or_create_model(
        #        ensemble_paths={"hist": path_for_hist for ens in ensembles},
        #        time_index=self.time_index,
        #        column_keys=["WOPTH:*", "WWPTH:*", "WGPTH:*"],
        #    )
        # )
        # df_smry_hist: pd.DataFrame = emodel_hist.get_or_load_smry_cached()
        # df_smry_hist = _get_filtered_df(
        #    df_smry_hist, excl_name_startswith, excl_name_contains
        # )
        # print(df_smry_hist)
        # t7 = time.time()

        # print(t5 - t1)
        # print(t6 - t5)

        # dframe_diff = _calcualte_diff_at_date(df_smry, df_smry_hist)
        # print(dframe_diff)

        self.set_callbacks(app)

    @property
    # def layout(self) -> wcc.FlexBox:
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
                    label="Well coverage crossplot",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        wcc.FlexBox(
                            id=self.uuid("well_coverage-layout"),
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
                                            id=self.uuid("ensemble_names"),
                                            options=[
                                                {"label": ens, "value": ens}
                                                for ens in self.ensembles
                                            ],
                                            value=self.ensembles,
                                            multi=True,
                                            clearable=False,
                                            persistence=True,
                                            persistence_type="memory",
                                        ),
                                        wcc.SelectWithLabel(
                                            label="Date selector",
                                            id=self.uuid("dates"),
                                            options=[
                                                {"label": _date, "value": _date}
                                                for _date in self.dates
                                            ],
                                            value=[self.dates[-1]],
                                            size=min([len(self.dates), 5]),
                                        ),
                                        wcc.SelectWithLabel(
                                            label="Phase selector",
                                            id=self.uuid("phases"),
                                            options=[
                                                {"label": phase, "value": phase}
                                                for phase in self.phases
                                            ],
                                            value=self.phases,
                                            size=min([len(self.phases), 3]),
                                        ),
                                        wcc.SelectWithLabel(
                                            label="Well selector",
                                            id=self.uuid("well_names"),
                                            options=[
                                                {"label": well, "value": well}
                                                for well in self.wells
                                            ],
                                            value=self.wells,
                                            size=min([len(self.wells), 9]),
                                        ),
                                        wcc.Dropdown(
                                            label="Colorby",
                                            id=self.uuid("colorby"),
                                            options=[
                                                {
                                                    "label": "Ensemble",
                                                    "value": "ENSEMBLE",
                                                },
                                                {"label": "Well", "value": "WELL"},
                                                {"label": "Date", "value": "DATE"},
                                            ],
                                            value="ENSEMBLE",
                                            multi=False,
                                            clearable=False,
                                            persistence=True,
                                            persistence_type="memory",
                                        ),
                                    ],
                                ),
                                wcc.Frame(
                                    style={"flex": 4, "minWidth": "500px"},
                                    children=[html.Div(id=self.uuid("coverage-graph"))],
                                    # children=[
                                    #     dcc.Graph(
                                    #         id=self.uuid("crossplot-graph"),
                                    #         style={"height": 500},
                                    #     ),
                                    # ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            # Output(self.uuid("crossplot-graph"), "figure"),
            Output(self.uuid("coverage-graph"), "children"),
            Input(self.uuid("ensemble_names"), "value"),
            Input(self.uuid("dates"), "value"),
            Input(self.uuid("phases"), "value"),
            Input(self.uuid("well_names"), "value"),
            Input(self.uuid("colorby"), "value"),
        )
        def _update_crossplot(
            ensemble_names, dates, phases, well_names, colorby
        ) -> px.scatter:

            dframe = self.df_stat

            # --- apply date filter
            dframe = dframe.loc[dframe["DATE"].isin(dates)]

            # --- apply ensemble filter
            dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

            # --- apply well filter
            dframe = dframe.loc[dframe["WELL"].isin(well_names)]

            # fig = update_crossplot(dframe)
            # return fig
            figures = update_coverage_plot(dframe, phases, colorby)
            return figures


# -----------------------------------
@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


# -----------------------------------
@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)


# -----------------------------------
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
                # print(realization.runpath())
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
        elif col in ["WOPT", "WWPT", "WGPT"]:
            vector, well = col.split(":")[0], col.split(":")[1]
            # print(vector, well)
            dframe[vector + "_DIFF:" + well] = (
                df_sim[col] - df_hist[vector + "H:" + well].values[0]
            )

    return dframe


# -------------------------------
def update_crossplot(df_stat):

    # df_stat_oil = df_stat[df_stat.VECTOR == "WOPT"]
    # df_stat_wat = df_stat[df_stat.VECTOR == "WWPT"]
    # df_stat_gas = df_stat[df_stat.VECTOR == "WGPT"]

    # print(df_stat)

    fig = px.scatter(
        df_stat,
        facet_row="VECTOR",
        category_orders={"VECTOR": ["WOPT", "WWPT", "WGPT"]},
        facet_row_spacing=0.03,
        x="OBS",
        y="SIM_MEAN",
        error_y=abs(df_stat["SIM_MEAN"] - df_stat["SIM_P10"]),
        error_y_minus=abs(df_stat["SIM_MEAN"] - df_stat["SIM_P90"]),
        text="WELL",
        color="ENSEMBLE",
    )
    fig.update_yaxes(matches=None)
    fig.update_xaxes(matches=None)

    # add zeroline (diagonal) for WOPT
    rmin = df_stat[df_stat.VECTOR == "WOPT"].OBS.min()
    rmax = df_stat[df_stat.VECTOR == "WOPT"].OBS.max()
    fig.add_trace(
        go.Scattergl(
            x=[rmin, rmax],
            y=[rmin, rmax],
            mode="lines",
            line_color="gray",
            name="zeroline",
            showlegend=None,
        ),
        row=3,
        col="all",
        exclude_empty_subplots=True,
    )

    # add zeroline (diagonal) for WWPT
    rmin = df_stat[df_stat.VECTOR == "WWPT"].OBS.min()
    rmax = max(
        df_stat[df_stat.VECTOR == "WWPT"].OBS.max(),
        df_stat[df_stat.VECTOR == "WWPT"].SIM_MEAN.max(),
    )
    fig.add_trace(
        go.Scattergl(
            x=[rmin, rmax],
            y=[rmin, rmax],
            mode="lines",
            line_color="gray",
            name="zeroline",
            showlegend=None,
        ),
        row=2,
        col="all",
        exclude_empty_subplots=True,
    )

    # add zeroline (diagonal) for WGPT
    rmin = df_stat[df_stat.VECTOR == "WGPT"].OBS.min()
    rmax = df_stat[df_stat.VECTOR == "WGPT"].OBS.max()
    fig.add_trace(
        go.Scattergl(
            x=[rmin, rmax],
            y=[rmin, rmax],
            mode="lines",
            line_color="gray",
            name="zeroline",
            showlegend=None,
        ),
        row=1,
        col="all",
        exclude_empty_subplots=True,
    )

    return fig


# -------------------------------
def update_coverage_plot(df_stat, phases, colorby):

    print("--- Updating coverage plot ---")

    figures = []
    figheight = 450
    # colorby = colorby

    # ---------------------------------------
    if "Oil" in phases:
        df_stat_oil = df_stat[df_stat.VECTOR == "WOPT"]
        fig_oil = px.scatter(
            df_stat_oil,
            x="OBS",
            y="SIM_MEAN",
            error_y=abs(df_stat_oil["SIM_MEAN"] - df_stat_oil["SIM_P10"]),
            error_y_minus=abs(df_stat_oil["SIM_MEAN"] - df_stat_oil["SIM_P90"]),
            text="WELL",
            color=colorby,
        )
        fig_oil.update_traces(textposition="middle left")

        # add zeroline (diagonal) for WOPT
        rmin = df_stat_oil.OBS.min()
        rmax = max(
            df_stat_oil.OBS.max(),
            df_stat_oil.SIM_MEAN.max(),
        )
        fig_oil.add_trace(
            go.Scattergl(
                x=[rmin, rmax],
                y=[rmin, rmax],
                mode="lines",
                line_color="rgb(0,100,80)",  # "gray",
                name="zeroline",
                showlegend=True,
            ),
        )

        # add 10% off-set for WOPT
        fig_oil.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.1, rmax * 1.1] + [rmax * 0.9, rmin * 0.9],
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±10% off-set",
                showlegend=True,
            ),
        )

        # add 20% off-set for WOPT
        fig_oil.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.2, rmax * 1.2] + [rmax * 0.8, rmin * 0.8],
                fill="toself",
                fillcolor="rgba(255, 99, 71, 0.1)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±20% off-set",
                showlegend=True,
            ),
        )

        figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    # ---------------------------------------
    if "Water" in phases:
        df_stat_wat = df_stat[df_stat.VECTOR == "WWPT"]
        fig_wat = px.scatter(
            df_stat_wat,
            x="OBS",
            y="SIM_MEAN",
            error_y=abs(df_stat_wat["SIM_MEAN"] - df_stat_wat["SIM_P10"]),
            error_y_minus=abs(df_stat_wat["SIM_MEAN"] - df_stat_wat["SIM_P90"]),
            text="WELL",
            color=colorby,
        )
        fig_wat.update_traces(textposition="middle left")

        # add zeroline (diagonal) for WWPT
        rmin = df_stat_wat.OBS.min()
        rmax = max(
            df_stat_wat.OBS.max(),
            df_stat_wat.SIM_MEAN.max(),
        )
        fig_wat.add_trace(
            go.Scattergl(
                x=[rmin, rmax],
                y=[rmin, rmax],
                mode="lines",
                line_color="gray",
                name="zeroline",
                showlegend=True,
            ),
        )

        # add 10% off-set for WWPT
        fig_wat.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.1, rmax * 1.1] + [rmax * 0.9, rmin * 0.9],
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±10% off-set",
                showlegend=True,
            ),
        )

        # add 20% off-set for WWPT
        fig_wat.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.2, rmax * 1.2] + [rmax * 0.8, rmin * 0.8],
                fill="toself",
                fillcolor="rgba(255, 99, 71, 0.1)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±20% off-set",
                showlegend=True,
            ),
        )

        figures.append(wcc.Graph(figure=fig_wat, style={"height": figheight}))

    # ---------------------------------------
    if "Gas" in phases:
        df_stat_gas = df_stat[df_stat.VECTOR == "WGPT"]
        fig_gas = px.scatter(
            df_stat_gas,
            x="OBS",
            y="SIM_MEAN",
            error_y=abs(df_stat_gas["SIM_MEAN"] - df_stat_gas["SIM_P10"]),
            error_y_minus=abs(df_stat_gas["SIM_MEAN"] - df_stat_gas["SIM_P90"]),
            text="WELL",
            color=colorby,
        )
        fig_gas.update_traces(textposition="middle left")

        # add zeroline (diagonal) for WGPT
        rmin = df_stat_gas.OBS.min()
        rmax = max(
            df_stat_gas.OBS.max(),
            df_stat_gas.SIM_MEAN.max(),
        )
        fig_gas.add_trace(
            go.Scattergl(
                x=[rmin, rmax],
                y=[rmin, rmax],
                mode="lines",
                line_color="gray",
                name="zeroline",
                showlegend=True,
            ),
        )

        # add 10% off-set for WGPT
        fig_gas.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.1, rmax * 1.1] + [rmax * 0.9, rmin * 0.9],
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±10% off-set",
                showlegend=True,
            ),
        )

        # add 20% off-set for WGPT
        fig_gas.add_trace(
            go.Scattergl(
                x=[rmin, rmax] + [rmax, rmin],
                y=[rmin * 1.2, rmax * 1.2] + [rmax * 0.8, rmin * 0.8],
                fill="toself",
                fillcolor="rgba(255, 99, 71, 0.1)",
                # mode="lines",
                line_color="rgba(255,255,255,0)",
                name="±20% off-set",
                showlegend=True,
            ),
        )

        figures.append(wcc.Graph(figure=fig_gas, style={"height": figheight}))

    return figures


# --------------------------------
def df_sim_ens_stat(df_smry: pd.DataFrame) -> pd.DataFrame:
    """Make a dataframe with ensemble statistics per well across all realizations.
    Return empty dataframe if no realizations included in df."""

    my_ensembles = []
    my_dates = []
    my_wells = []
    my_sim_vectors = []
    my_sim_mean_values = []
    my_sim_std_values = []
    my_sim_p10_values = []
    my_sim_p90_values = []
    my_hist_values = []

    for ens_name, dframe in df_smry.groupby("ENSEMBLE"):
        for _date, ensdf in dframe.groupby("DATE"):

            for col in ensdf.columns:
                if ":" in col:
                    vector = col.split(":")[0]
                    if vector in ["WOPT", "WWPT", "WGPT", "WL PT"]:
                        well = col.split(":")[1]
                        my_wells.append(well)
                        my_dates.append(_date)
                        my_ensembles.append(ens_name)
                        my_sim_vectors.append(vector)
                        my_sim_mean_values.append(ensdf[col].mean())
                        my_sim_std_values.append(ensdf[col].std())
                        my_sim_p10_values.append(ensdf[col].quantile(0.9))
                        my_sim_p90_values.append(ensdf[col].quantile(0.1))
                        my_hist_values.append(ensdf[vector + "H:" + well].mean())

    df_stat = pd.DataFrame(
        data={
            "ENSEMBLE": my_ensembles,
            "WELL": my_wells,
            "VECTOR": my_sim_vectors,
            "DATE": my_dates,
            "OBS": my_hist_values,
            "SIM_MEAN": my_sim_mean_values,
            "SIM_STD": my_sim_std_values,
            "SIM_P10": my_sim_p10_values,
            "SIM_P90": my_sim_p90_values,
        }
    )
    df_stat = df_stat.astype({"DATE": "string"})
    return df_stat
