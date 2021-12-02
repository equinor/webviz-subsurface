import logging
import time
from pathlib import Path
from .types.provider_set import (
    create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc

from ._callbacks import plugin_callbacks
from ._layout import main_layout

# import webviz_subsurface_components as wsc
from dash import Input, Output  # , html  # Dash, State, dcc,

# from dash.exceptions import PreventUpdate
from fmu import ensemble

# from plotly.subplots import make_subplots
from webviz_config import WebvizPluginABC, WebvizSettings  # EncodedFile,
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)
from webviz_subsurface._providers import Frequency

# Color scales
SYMMETRIC = [
    [0, "gold"],
    [0.1, "red"],
    [0.3, "darkred"],
    [0.4, "dimgrey"],
    [0.45, "lightgrey"],
    [0.5, "WhiteSmoke"],
    [0.55, "lightgrey"],
    [0.6, "dimgrey"],
    [0.7, "darkblue"],
    [0.9, "blue"],
    [1, "cyan"],
]


class ProdMisfit(WebvizPluginABC):
    """Visualizes production data misfit at selected date.

    **Features**
    * Visualization of prod misfit at selected time.
    * Visualization of prod coverage at selected time.

    ---
    xxx
    ---
    yyy
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        # sampling: Union[str, list] # make it possible to add user specified date list?
        sampling: str = Frequency.YEARLY.value,  # "yearly"
        # perform_presampling: bool = True,
        excl_name_startswith: list = None,
        excl_name_contains: list = None,
        weight_reduction_factor_oil: float = 1.0,
        weight_reduction_factor_wat: float = 1.0,
        weight_reduction_factor_gas: float = 300.0,
    ):

        super().__init__()

        start = time.time()

        self.weight_reduction_factor_oil = weight_reduction_factor_oil
        self.weight_reduction_factor_wat = weight_reduction_factor_wat
        self.weight_reduction_factor_gas = weight_reduction_factor_gas

        # Must define valid freqency
        self._sampling = Frequency(sampling)

        ensemble_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        self._input_provider_set = create_presampled_provider_set_from_paths(
            ensemble_paths, self._sampling
        )
        # self._input_provider_set.verify_consistent_vector_metadata()

        logging.debug(f"Created provider_set. Cummulative time: {time.time() - start}")

        self.ensemble_names = self._input_provider_set.names()

        self.dates = {}
        self.realizations = {}
        self.wells = {}
        self.vectors = {}
        self.phases = {}

        for ens_name in self.ensemble_names:
            logging.info(f"Working with: {ens_name}")
            ens_provider = self._input_provider_set.provider(ens_name)
            self.realizations[ens_name] = ens_provider.realizations()
            self.dates[ens_name] = ens_provider.dates(resampling_frequency=None)
            # [_date.strftime("%Y-%m-%d") for _date in self.dates[ens_name]]

            (  # from wopt/wwpt/wgpt: get lists of wells, vectors and phases
                self.wells[ens_name],
                self.vectors[ens_name],
                self.phases[ens_name],
            ) = _get_wells_vectors_phases(
                ens_provider.vector_names(), excl_name_startswith, excl_name_contains
            )

        # self.realizations = self._input_provider_set.all_realizations()
        # all_vectors = self._input_provider_set.all_vector_names()

        # -----------------------------------------

        # df_smry = self._input_provider_set.provider(
        #     self.ensemble_names[0]
        # ).get_vectors_df(self.vectors, None, None)
        # print(df_smry)

        # # Calculate statistics
        # self.df_stat = get_df_stat(df_smry)

        # # Calculate diffs and diff statistics
        # self.df_diff = get_df_diff(df_smry)
        # self.df_diff_stat = get_df_diff_stat(self.df_diff)
        # logging.debug(f"Diff stat\n{self.df_diff_stat}")

        # # get list of groups
        # self.groups = sorted(
        #     list(self.df_stat[self.df_stat["VECTOR"].str.startswith("G")].WELL.unique())
        # )
        # logging.info(f"\nGroups: {self.groups}")

        self.set_callbacks(app)

        logging.debug(f"Init done. Cummulative time: {time.time() - start}")

        # logging.debug(f"df_smry:\n{df_smry}")
        # logging.debug(f"df_stat:\n{self.df_stat}")
        # logging.debug(f"df_diff:\n{self.df_diff}")
        # logging.debug(f"df_diff_stat:\n{self.df_diff_stat}")

    @property
    def layout(self) -> wcc.Tabs:
        return main_layout(
            get_uuid=self.uuid,
            ensemble_names=self.ensemble_names,
            dates=self.dates,
            phases=self.phases,
            wells=self.wells,
            realizations=self.realizations,
        )

    # ---------------------------------------------
    def set_callbacks(self, app: dash.Dash) -> None:
        plugin_callbacks(
            app=app,
            get_uuid=self.uuid,
            input_provider_set=self._input_provider_set,
            ens_vectors=self.vectors,
            ens_realizations=self.realizations,
            weight_reduction_factor_oil=self.weight_reduction_factor_oil,
            weight_reduction_factor_wat=self.weight_reduction_factor_wat,
            weight_reduction_factor_gas=self.weight_reduction_factor_gas,
        )


# -----------------------------------
@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


# -----------------------------------
@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)


# ------------------------------------------------------------------------
# plot, dataframe and support functions below here
# ------------------------------------------------------------------------


def _get_filtered_df(
    dframe: pd.DataFrame, excl_name_startswith: list, excl_name_contains: list
) -> pd.DataFrame:
    """Remove unwanted wells/groups from dframe"""

    drop_list = []
    for colname in dframe.columns:
        if ":" in colname:
            name = colname.split(":")[1]
            if name.startswith(tuple(excl_name_startswith)):
                drop_list.append(colname)
                continue
            # else:
            for excl in excl_name_contains:
                if excl in name:
                    drop_list.append(colname)
                    continue
    if len(drop_list) > 0:
        logging.info(f"\nDropping column keys: {drop_list}")
    return dframe.drop(columns=drop_list)


def _calcualte_diff_at_date(
    df_sim: pd.DataFrame, df_hist: pd.DataFrame
) -> pd.DataFrame:
    """Calculate diff (sim - obs)."""

    date = df_sim.DATE.values[2]
    dframe = pd.DataFrame()
    df_sim = df_sim[df_sim.DATE == date]
    df_hist = df_hist[df_hist.DATE == date]
    for col in df_sim.columns:
        if col in ["REAL", "ENSEMBLE", "DATE"]:
            dframe[col] = df_sim[col]
        elif col in ["WOPT", "WWPT", "WGPT", "GOPT", "GWPT", "GGPT"]:
            vector, well = col.split(":")[0], col.split(":")[1]
            # logging.debug(f"{vector} {well}")
            dframe[vector + "_DIFF:" + well] = (
                df_sim[col] - df_hist[vector + "H:" + well].values[0]
            )

    return dframe


# -------------------------------
def update_coverage_crossplot(
    df_stat: pd.DataFrame, phases: list, colorby: str, vector_type: str = "well"
) -> List[wcc.Graph]:

    logging.debug("--- Updating coverage plot ---")

    figures = []
    figheight = 400
    # logging.debug(phases, colorby, vector_type, "\n", df_stat, "\n")

    if vector_type == "group":
        oil_vector, wat_vector, gas_vector = "GOPT", "GWPT", "GGPT"
    elif vector_type == "well":
        oil_vector, wat_vector, gas_vector = "WOPT", "WWPT", "WGPT"
    else:
        raise ValueError(
            "vector_type = ",
            vector_type,
            ". 'vector_type' argument must be 'well' or 'group'",
        )

    # ---------------------------------------
    if "Oil" in phases:
        df_stat_oil = df_stat[df_stat.VECTOR == oil_vector]
        _p10 = abs(df_stat_oil["SIM_MEAN"] - df_stat_oil["SIM_P10"])
        _p90 = abs(df_stat_oil["SIM_MEAN"] - df_stat_oil["SIM_P90"])
        fig_oil = px.scatter(
            df_stat_oil,
            x="OBS",
            y="SIM_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            text="WELL",
            color=colorby,
        )
        fig_oil.update_traces(textposition="middle left")

        # add zeroline (diagonal) for oil_vector
        rmin = min(df_stat_oil.OBS.min(), df_stat_oil.SIM_MEAN.min())
        rmax = max(df_stat_oil.OBS.max(), df_stat_oil.SIM_MEAN.max())
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

        # add 10% off-set for oil_vector
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

        # add 20% off-set for oil_vector
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

        fig_oil.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_oil.update_xaxes(title_text="Obs/hist")
        fig_oil.update_yaxes(title_text="Sim mean ± p10/p90")
        figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    # ---------------------------------------
    if "Water" in phases:
        df_stat_wat = df_stat[df_stat.VECTOR == wat_vector]
        _p10 = abs(df_stat_wat["SIM_MEAN"] - df_stat_wat["SIM_P10"])
        _p90 = abs(df_stat_wat["SIM_MEAN"] - df_stat_wat["SIM_P90"])
        fig_wat = px.scatter(
            df_stat_wat,
            x="OBS",
            y="SIM_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            text="WELL",
            color=colorby,
        )
        fig_wat.update_traces(textposition="middle left")

        # add zeroline (diagonal) for wat_vector
        rmin = min(df_stat_wat.OBS.min(), df_stat_wat.SIM_MEAN.min())
        rmax = max(df_stat_wat.OBS.max(), df_stat_wat.SIM_MEAN.max())
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

        # add 10% off-set for wat_vector
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

        # add 20% off-set for wat_vector
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

        fig_wat.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_wat.update_xaxes(title_text="Obs/hist")
        fig_wat.update_yaxes(title_text="Sim mean ± p10/p90")
        figures.append(wcc.Graph(figure=fig_wat, style={"height": figheight}))

    # ---------------------------------------
    if "Gas" in phases:
        df_stat_gas = df_stat[df_stat.VECTOR == gas_vector]
        _p10 = abs(df_stat_gas["SIM_MEAN"] - df_stat_gas["SIM_P10"])
        _p90 = abs(df_stat_gas["SIM_MEAN"] - df_stat_gas["SIM_P90"])
        fig_gas = px.scatter(
            df_stat_gas,
            x="OBS",
            y="SIM_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            text="WELL",
            color=colorby,
        )
        fig_gas.update_traces(textposition="middle left")

        # add zeroline (diagonal) for gas_vector
        rmin = min(df_stat_gas.OBS.min(), df_stat_gas.SIM_MEAN.min())
        rmax = max(df_stat_gas.OBS.max(), df_stat_gas.SIM_MEAN.max())
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

        # add 10% off-set for gas_vector
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

        # add 20% off-set for gas_vector
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

        fig_gas.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_gas.update_xaxes(title_text="Obs/hist")
        fig_gas.update_yaxes(title_text="Sim mean ± p10/p90")
        figures.append(wcc.Graph(figure=fig_gas, style={"height": figheight}))

    return figures


# -------------------------------
def update_coverage_boxplot(
    df_diff: pd.DataFrame,
    phases: list,
    colorby: str,
    vector_type: str = "well",
    figheight: int = 450,
) -> List[wcc.Graph]:
    """Create plot of misfit per well. One plot per phase."""

    logging.debug("--- Updating coverage box plot ---")
    figures = []

    # --- drop columns (realizations) with no data
    ensdf = df_diff.dropna(axis="columns")

    if vector_type == "group":
        oil_vector, wat_vector, gas_vector = "DIFF_GOPT", "DIFF_GWPT", "DIFF_GGPT"
    elif vector_type == "well":
        oil_vector, wat_vector, gas_vector = "DIFF_WOPT", "DIFF_WWPT", "DIFF_WGPT"
    else:
        raise ValueError(
            "vector_type = ",
            vector_type,
            ". 'vector_type' argument must be 'well' or 'group'",
        )

    all_columns = list(ensdf)  # column names

    if "Oil" in phases:
        oil_columns = [x for x in all_columns if x.startswith(oil_vector)]
        fig_oil = px.box(ensdf, y=oil_columns, color="ENSEMBLE")
        figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    return figures


# -------------------------------
def update_coverage_diff_plot(
    df_diff_stat: pd.DataFrame,
    phases: list,
    colorby: str,
    vector_type: str = "well",
    figheight: int = 450,
) -> List[wcc.Graph]:
    """Create plot of misfit per well. One plot per phase."""

    logging.debug("--- Updating coverage diff plot ---")
    figures = []

    if vector_type == "group":
        oil_vector, wat_vector, gas_vector = "DIFF_GOPT", "DIFF_GWPT", "DIFF_GGPT"
    elif vector_type == "well":
        oil_vector, wat_vector, gas_vector = "DIFF_WOPT", "DIFF_WWPT", "DIFF_WGPT"
    else:
        raise ValueError(
            "vector_type = ",
            vector_type,
            ". 'vector_type' argument must be 'well' or 'group'",
        )

    # -------------------------
    if "Oil" in phases:
        df_diff_stat_oil = df_diff_stat[df_diff_stat.VECTOR == oil_vector]
        # logging.debug(f"Dataframe, diff oil phase:\n{df_diff_stat_oil}")
        _p10 = abs(df_diff_stat_oil["DIFF_MEAN"] - df_diff_stat_oil["DIFF_P10"])
        _p90 = abs(df_diff_stat_oil["DIFF_MEAN"] - df_diff_stat_oil["DIFF_P90"])
        fig_oil = px.scatter(
            df_diff_stat_oil,
            x="WELL",
            y="DIFF_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            # text="WELL",
            color=colorby,
        )
        # fig_oil.update_traces(textposition="middle left")
        fig_oil.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_oil.update_xaxes(title_text="Well")
        fig_oil.update_yaxes(title_text="Oil mismatch ± p10/p90")
        fig_oil.add_hline(0)

        figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    # -------------------------
    if "Water" in phases:
        df_diff_stat_wat = df_diff_stat[df_diff_stat.VECTOR == wat_vector]
        # logging.debug(f"Dataframe, diff water phase:\n{df_diff_stat_wat}")
        _p10 = abs(df_diff_stat_wat["DIFF_MEAN"] - df_diff_stat_wat["DIFF_P10"])
        _p90 = abs(df_diff_stat_wat["DIFF_MEAN"] - df_diff_stat_wat["DIFF_P90"])
        fig_wat = px.scatter(
            df_diff_stat_wat,
            x="WELL",
            y="DIFF_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            # text="WELL",
            color=colorby,
        )
        # fig_wat.update_traces(textposition="middle left")
        fig_wat.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_wat.update_xaxes(title_text="Well")
        fig_wat.update_yaxes(title_text="Water mismatch ± p10/p90")
        fig_wat.add_hline(0)

        figures.append(wcc.Graph(figure=fig_wat, style={"height": figheight}))

    # -------------------------
    if "Gas" in phases:
        df_diff_stat_gas = df_diff_stat[df_diff_stat.VECTOR == gas_vector]
        # logging.debug(f"Dataframe, diff gas phase:\n{df_diff_stat_gas}")
        _p10 = abs(df_diff_stat_gas["DIFF_MEAN"] - df_diff_stat_gas["DIFF_P10"])
        _p90 = abs(df_diff_stat_gas["DIFF_MEAN"] - df_diff_stat_gas["DIFF_P90"])
        fig_gas = px.scatter(
            df_diff_stat_gas,
            x="WELL",
            y="DIFF_MEAN",
            error_y=_p10,
            error_y_minus=_p90,
            # text="WELL",
            color=colorby,
        )
        # fig_gas.update_traces(textposition="middle left")
        fig_gas.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig_gas.update_xaxes(title_text="Well")
        fig_gas.update_yaxes(title_text="Gas mismatch ± p10/p90")
        fig_gas.add_hline(0)

        figures.append(wcc.Graph(figure=fig_gas, style={"height": figheight}))

    return figures


# -------------------------------
def update_heatmap_plot(
    df_diff_stat: pd.DataFrame,
    phases: list,
    vector_type: str = "well",
    filter_largest: int = 10,
    figheight: int = 450,
    scale_col_range: float = 1.0,
) -> List[wcc.Graph]:
    """Create heatmap of misfit per well or group. One plot per phase."""

    logging.debug("--- Updating heatmap ---")
    figures = []

    if vector_type == "group":
        oil_vector, wat_vector, gas_vector = "DIFF_GOPT", "DIFF_GWPT", "DIFF_GGPT"
    elif vector_type == "well":
        oil_vector, wat_vector, gas_vector = "DIFF_WOPT", "DIFF_WWPT", "DIFF_WGPT"
    else:
        raise ValueError(
            "vector_type = ",
            vector_type,
            ". 'vector_type' argument must be 'well' or 'group'",
        )

    # -------------------------
    if "Oil" in phases:
        df_diff_stat_oil = df_diff_stat[df_diff_stat.VECTOR == oil_vector]
        # logging.debug(f"Dataframe, diff oil phase:\n{df_diff_stat_oil}")

        zmax = scale_col_range * max(
            abs(df_diff_stat_oil.DIFF_MEAN.max()), abs(df_diff_stat_oil.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_oil.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            # logging.debug(
            #     f"Dataframe pivot table, {ens_name} diff oil phase:\n{df_pivot}"
            # )

            fig_oil = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_oil.update_layout(
                title_text=f"{ens_name} - Oil cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_oil.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    # -------------------------
    if "Water" in phases:
        df_diff_stat_wat = df_diff_stat[df_diff_stat.VECTOR == wat_vector]

        zmax = scale_col_range * max(
            abs(df_diff_stat_wat.DIFF_MEAN.max()), abs(df_diff_stat_wat.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_wat.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            fig_wat = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_wat.update_layout(
                title_text=f"{ens_name} - Wat cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_wat.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_wat, style={"height": figheight}))

    # -------------------------
    if "Gas" in phases:
        df_diff_stat_gas = df_diff_stat[df_diff_stat.VECTOR == gas_vector]

        zmax = scale_col_range * max(
            abs(df_diff_stat_gas.DIFF_MEAN.max()), abs(df_diff_stat_gas.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_gas.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            fig_gas = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_gas.update_layout(
                title_text=f"{ens_name} - Gas cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_gas.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_gas, style={"height": figheight}))

    return figures


# --------------------------------
def get_df_stat(df_smry: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with ensemble statistics per well across all realizations.
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
                    if vector in [
                        "WOPT",
                        "WWPT",
                        "WGPT",
                        "GOPT",
                        "GWPT",
                        "GGPT",
                    ]:
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


# --------------------------------
def get_df_diff_stat(df_diff: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with ensemble statistics of production
    difference per well across all realizations.
    Return empty dataframe if no realizations included in df."""

    my_ensembles = []
    my_dates = []
    my_wells = []
    my_diff_vectors = []
    my_diff_mean_values = []
    my_diff_std_values = []
    my_diff_p10_values = []
    my_diff_p90_values = []

    for ens_name, dframe in df_diff.groupby("ENSEMBLE"):
        for _date, ensdf in dframe.groupby("DATE"):

            for col in ensdf.columns:
                if ":" in col:
                    vector = col.split(":")[0]
                    if vector in [
                        "DIFF_WOPT",
                        "DIFF_WWPT",
                        "DIFF_WGPT",
                        "DIFF_GOPT",
                        "DIFF_GWPT",
                        "DIFF_GGPT",
                    ]:
                        well = col.split(":")[1]
                        my_wells.append(well)
                        my_dates.append(_date)
                        my_ensembles.append(ens_name)
                        my_diff_vectors.append(vector)
                        my_diff_mean_values.append(ensdf[col].mean())
                        my_diff_std_values.append(ensdf[col].std())
                        my_diff_p10_values.append(ensdf[col].quantile(0.9))
                        my_diff_p90_values.append(ensdf[col].quantile(0.1))

    df_stat = pd.DataFrame(
        data={
            "ENSEMBLE": my_ensembles,
            "WELL": my_wells,
            "VECTOR": my_diff_vectors,
            "DATE": my_dates,
            "DIFF_MEAN": my_diff_mean_values,
            "DIFF_STD": my_diff_std_values,
            "DIFF_P10": my_diff_p10_values,
            "DIFF_P90": my_diff_p90_values,
        }
    )
    df_stat = df_stat.astype({"DATE": "string"})
    return df_stat


# # --------------------------------
# def _df_filter_wells(
#     dframe: pd.DataFrame, wells: list, keep_wells: list
# ) -> pd.DataFrame:
#     """Return dataframe without any of the wells not in keep_wells list"""

#     # --- apply well filter
#     exclude_wells = set(wells) ^ set(keep_wells)
#     drop_col = []
#     for col in dframe.columns:
#         if ":" in col:
#             for well in exclude_wells:
#                 if well == col.split(":")[1]:  # only drop exact matches
#                     drop_col.append(col)
#                     break
#     return dframe.drop(drop_col, axis=1)


# --------------------------------
def _get_wells_vectors_phases(
    vector_names: list, excl_name_startswith: list, excl_name_contains: list
) -> Tuple[List, List, List]:
    """Return lists of wells, vectors and phases."""

    drop_list = []
    wells, vectors = [], []
    oil_phase, wat_phase, gas_phase = False, False, False
    for vector in vector_names:
        if vector.startswith(("WOPT:", "WWPT:", "WGPT:")):
            well = vector.split(":")[1]
            vector_type = vector.split(":")[0]
            if well.startswith(tuple(excl_name_startswith)):
                drop_list.append(well)
                continue
            for excl in excl_name_contains:
                if excl in well:
                    drop_list.append(well)
                    continue
            if well not in wells:
                wells.append(well)
            if vector not in vectors:
                vectors.append(vector)
                if vector_type == "WOPT":
                    oil_phase = True
                if vector_type == "WWPT":
                    wat_phase = True
                if vector_type == "WGPT":
                    gas_phase = True
    wells, vectors = sorted(wells), sorted(vectors)

    if len(drop_list) > 0:
        logging.info(f"\nDropping wells: {list(sorted(set(drop_list)))}")

    if len(vectors) == 0:
        RuntimeError("No WOPT, WWPT or WGPT vectors found.")

    phases = ["Oil", "Water", "Gas"]
    # remove phases not present
    if not oil_phase:
        phases.remove("Oil")
    if not wat_phase:
        phases.remove("Water")
    if not gas_phase:
        phases.remove("Gas")

    logging.info(f"\nWells: {wells}")
    logging.info(f"\nPhases: {phases}")
    logging.info(f"\nVectors: {vectors}")

    return wells, vectors, phases
