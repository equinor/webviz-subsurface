# pylint: disable=too-many-lines
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union  # Callable, Tuple,

import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc

# import webviz_subsurface_components as wsc
from dash import Input, Output, html  # Dash, State, dcc,

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

from _callbacks import plugin_callbacks
from _layout import main_layout

from .types.provider_set import (
    create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)

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
        ensembles: list = None,
        # sampling: Union[str, list] = "yearly",
        sampling: str = Frequency.YEARLY.value,  # "yearly"
        perform_presampling: bool = True,
        excl_name_startswith: list = None,
        excl_name_contains: list = None,
        misfit_weight_oil: float = 1.0,
        misfit_weight_wat: float = 1.0,
        misfit_weight_gas: float = 300.0,
    ):

        super().__init__()

        start = time.time()

        self.misfit_weight_oil = misfit_weight_oil
        self.misfit_weight_wat = misfit_weight_wat
        self.misfit_weight_gas = misfit_weight_gas

        # Must define valid freqency
        self._sampling = Frequency(sampling)

        perform_presampling = True

        if ensembles is not None:
            ensemble_paths: Dict[str, Path] = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            if perform_presampling:
                self._input_provider_set = create_presampled_provider_set_from_paths(
                    ensemble_paths, self._sampling
                )
            else:
                self._input_provider_set = create_lazy_provider_set_from_paths(
                    ensemble_paths
                )

            self._input_provider_set.verify_consistent_vector_metadata()

        else:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles"'
            )

        logging.debug(f"Done reading summary. Cummulative time: {time.time() - start}")

        # -----------------------------------------
        # auto-remove columns/vectors with all zeros
        # df_smry = df_smry.loc[:, (df_smry != 0).any(axis=0)]

        # -----------------------------------------
        # remove columns if in excl_name_startswith or excl_name_contains
        df_smry = _get_filtered_df(df_smry, excl_name_startswith, excl_name_contains)

        # Calculate statistics
        self.df_stat = get_df_stat(df_smry)

        # Calculate diffs and diff statistics
        self.df_diff = get_df_diff(df_smry)
        self.df_diff_stat = get_df_diff_stat(self.df_diff)
        logging.debug(f"Diff stat\n{self.df_diff_stat}")

        # get list of realizations
        self.realizations = sorted(list(self.df_diff.REAL.unique()))

        # get list of dates
        self.dates = sorted(list(self.df_stat.DATE.unique()))

        # get list of wells
        self.wells = sorted(
            list(self.df_stat[self.df_stat["VECTOR"].str.startswith("W")].WELL.unique())
        )
        logging.info(f"\nWells: {self.wells}")

        # get list of groups
        self.groups = sorted(
            list(self.df_stat[self.df_stat["VECTOR"].str.startswith("G")].WELL.unique())
        )
        logging.info(f"\nGroups: {self.groups}")

        # get list of phases
        self.phases = ["Oil", "Water", "Gas"]
        vectors = list(self.df_stat.VECTOR.unique())
        if "WOPT" not in vectors:
            self.phases.remove("Oil")
        if "WWPT" not in vectors:
            self.phases.remove("Water")
        if "WGPT" not in vectors:
            self.phases.remove("Gas")

        self.set_callbacks(app)

        logging.debug(f"Init done. Cummulative time: {time.time() - start}")
        logging.debug(f"df_smry:\n{df_smry}")
        logging.debug(f"df_stat:\n{self.df_stat}")
        logging.debug(f"df_diff:\n{self.df_diff}")
        logging.debug(f"df_diff_stat:\n{self.df_diff_stat}")

    @property
    def layout(self) -> wcc.Tabs:
        return main_layout(
            get_uuid=self.uuid,
            ensemble_names=self._input_provider_set.names(),
        )

    # ---------------------------------------------
    def set_callbacks(self, app: dash.Dash) -> None:

        # --------------------------------------------
        # --- prod misfit ---
        # --------------------------------------------
        @app.callback(
            Output(self.uuid("prod_misfit-graph"), "children"),
            Input(self.uuid("prod_misfit-ensemble_names"), "value"),
            Input(self.uuid("prod_misfit-dates"), "value"),
            Input(self.uuid("prod_misfit-phases"), "value"),
            Input(self.uuid("prod_misfit-well_names"), "value"),
            Input(self.uuid("prod_misfit-realizations"), "value"),
            Input(self.uuid("prod_misfit-colorby"), "value"),
            Input(self.uuid("prod_misfit-sorting"), "value"),
            Input(self.uuid("prod_misfit-figheight"), "value"),
        )
        def _update_prod_misfit_graph(
            ensemble_names: List[str],
            dates: list,
            phases: list,
            well_names: list,
            realizations: List[Union[int, str]],
            colorby: str,
            sorting: str,
            figheight: int,
        ) -> List[wcc.Graph]:

            dframe = self.df_diff

            # --- apply date filter
            dframe = dframe.loc[dframe["DATE"].isin(dates)]

            # --- apply ensemble filter
            dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

            # --- apply realization filter
            dframe = dframe.loc[dframe["REAL"].isin(realizations)]

            # --- apply well filter
            dframe = _df_filter_wells(dframe, self.wells, well_names)

            figures = update_prod_misfit_plot(
                dframe,
                phases,
                colorby,
                sorting,
                figheight,
                misfit_weight_oil=self.misfit_weight_oil,
                misfit_weight_wat=self.misfit_weight_wat,
                misfit_weight_gas=self.misfit_weight_gas,
            )
            return figures

        # --------------------------------------------
        # --- well coverage ---
        # --------------------------------------------
        @app.callback(
            Output(self.uuid("well_coverage-graph"), "children"),
            Input(self.uuid("well_coverage-ensemble_names"), "value"),
            Input(self.uuid("well_coverage-dates"), "value"),
            Input(self.uuid("well_coverage-phases"), "value"),
            Input(self.uuid("well_coverage-well_names"), "value"),
            Input(self.uuid("well_coverage-colorby"), "value"),
            Input(self.uuid("well_coverage-plot_type"), "value"),
        )
        def _update_well_coverage_graph(
            ensemble_names: List[str],
            dates: list,
            phases: list,
            well_names: list,
            colorby: str,
            plot_type: str,
        ) -> List[wcc.Graph]:

            if plot_type == "boxplot":
                dframe = self.df_diff.copy()
            elif plot_type == "crossplot":
                dframe = self.df_stat.copy()
            else:
                dframe = self.df_diff_stat.copy()

            # --- apply date filter
            dframe = dframe.loc[dframe["DATE"].isin(dates)]

            # --- apply ensemble filter
            dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

            # --- apply well filter
            # dframe = dframe.loc[dframe["WELL"].isin(well_names)]

            if plot_type == "boxplot":
                figures = update_coverage_boxplot(
                    dframe,
                    phases,
                    colorby,
                    vector_type="well",
                )
            elif plot_type == "crossplot":
                figures = update_coverage_crossplot(
                    dframe,
                    phases,
                    colorby,
                    vector_type="well",
                )
            else:
                figures = update_coverage_diff_plot(
                    dframe,
                    phases,
                    colorby,
                    vector_type="well",
                )
            return figures

        # --------------------------------------------
        # --- group coverage ---
        # --------------------------------------------
        @app.callback(
            Output(self.uuid("group_coverage-graph"), "children"),
            Input(self.uuid("group_coverage-ensemble_names"), "value"),
            Input(self.uuid("group_coverage-dates"), "value"),
            Input(self.uuid("group_coverage-phases"), "value"),
            Input(self.uuid("group_coverage-group_names"), "value"),
            Input(self.uuid("group_coverage-colorby"), "value"),
            Input(self.uuid("group_coverage-plot_type"), "value"),
            # prevent_initial_call=True,
        )
        def _update_group_coverage_graph(
            ensemble_names: List[str],
            dates: list,
            phases: list,
            group_names: list,
            colorby: str,
            plot_type: str,
        ) -> List[wcc.Graph]:

            if plot_type == "crossplot":
                dframe = self.df_stat.copy()
            else:
                dframe = self.df_diff_stat.copy()

            # --- apply date filter
            dframe = dframe.loc[dframe["DATE"].isin(dates)]

            # --- apply ensemble filter
            dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

            # --- apply group filter
            dframe = dframe.loc[dframe["WELL"].isin(group_names)]

            if plot_type == "crossplot":
                figures = update_coverage_crossplot(
                    dframe,
                    phases,
                    colorby,
                    vector_type="group",
                )
            else:
                figures = update_coverage_diff_plot(
                    dframe,
                    phases,
                    colorby,
                    vector_type="group",
                )
            return figures

        # --------------------------------------------
        # --- heatmap ---
        # --------------------------------------------
        @app.callback(
            Output(self.uuid("heatmap-graph"), "children"),
            Input(self.uuid("heatmap-ensemble_names"), "value"),
            Input(self.uuid("heatmap-dates"), "value"),
            Input(self.uuid("heatmap-phases"), "value"),
            Input(self.uuid("heatmap-well_names"), "value"),
            Input(self.uuid("heatmap-filter_largest"), "value"),
            Input(self.uuid("heatmap-figheight"), "value"),
            Input(self.uuid("heatmap-scale_col_range"), "value"),
            # prevent_initial_call=True,
        )
        def _update_heatmap_graph(
            ensemble_names: List[str],
            dates: list,
            phases: list,
            well_names: list,
            filter_largest: int,
            figheight: int,
            scale_col_range: float,
        ) -> List[wcc.Graph]:

            dframe = self.df_diff_stat.copy()

            # --- apply date filter
            dframe = dframe.loc[dframe["DATE"].isin(dates)]

            # --- apply ensemble filter
            dframe = dframe.loc[dframe["ENSEMBLE"].isin(ensemble_names)]

            # --- apply well filter
            dframe = dframe.loc[dframe["WELL"].isin(well_names)]

            figures = update_heatmap_plot(
                dframe,
                phases,
                vector_type="well",
                filter_largest=filter_largest,
                figheight=figheight,
                scale_col_range=scale_col_range,
            )
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


# ------------------------------------------------------------------------
# plot, dataframe and support functions below here
# ------------------------------------------------------------------------

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

    ok_file = "OK"
    result: set = set()

    for ens_name in ensembles:
        path = webviz_settings.shared_settings["scratch_ensembles"][ens_name]
        ensset = ensemble.EnsembleSet("ensset", frompath=path)
        for ens in ensset._ensembles.values():
            for realization in ens.realizations.values():
                # logging.debug(realization.runpath())
                if realization.contains(ok_file):
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

    column_keys = []
    for vec in smry_vectors:
        for well in well_list:
            column_keys.append(vec + ":" + well)

    return column_keys


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
def update_prod_misfit_plot(
    df_diff: pd.DataFrame,
    phases: list,
    colorby: str,
    sorting: str = None,
    figheight: int = 450,
    misfit_weight_oil: float = 1.0,
    misfit_weight_wat: float = 1.0,
    misfit_weight_gas: float = 300,
    misfit_exponent: float = 1.0,
    normalize: bool = False,
) -> List[wcc.Graph]:
    """Create plot of misfit per realization. One plot per ensemble.
    Misfit is absolute value of |sim - obs|, weighted by obs_error"""

    logging.debug("--- Updating production misfit plot ---")
    max_misfit, min_misfit = 0, 0
    figures = []

    for ens_name, ensdf in df_diff.groupby("ENSEMBLE"):

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        all_columns = list(ensdf)  # column names

        df_misfit = ensdf[["ENSEMBLE", "DATE", "REAL"]].copy()
        df_misfit = df_misfit.astype({"REAL": "string"})
        df_misfit["TOTAL_MISFIT"] = 0

        plot_phases = []
        color_phases = {}

        # -------------------------
        if "Oil" in phases:
            oil_columns = [x for x in all_columns if x.startswith("DIFF_WOPT")]
            df_misfit["OIL_MISFIT"] = (
                ensdf[oil_columns].abs().sum(axis=1) / misfit_weight_oil
            )
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["OIL_MISFIT"]
            )
            plot_phases.append("OIL_MISFIT")
            color_phases["OIL_MISFIT"] = "#2ca02c"
        # -------------------------
        if "Water" in phases:
            wat_columns = [x for x in all_columns if x.startswith("DIFF_WWPT")]
            df_misfit["WAT_MISFIT"] = (
                ensdf[wat_columns].abs().sum(axis=1) / misfit_weight_wat
            )
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["WAT_MISFIT"]
            )
            plot_phases.append("WAT_MISFIT")
            color_phases["WAT_MISFIT"] = "#1f77b4"
        # -------------------------
        if "Gas" in phases:
            gas_columns = [x for x in all_columns if x.startswith("DIFF_WGPT")]
            df_misfit["GAS_MISFIT"] = (
                ensdf[gas_columns].abs().sum(axis=1) / misfit_weight_gas
            )
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["GAS_MISFIT"]
            )
            plot_phases.append("GAS_MISFIT")
            color_phases["GAS_MISFIT"] = "#d62728"
        # -------------------------

        if (
            max_misfit == min_misfit == 0
        ):  # caclulate min-max ranges from first ensemble
            for _, df_date in df_misfit.groupby("DATE"):
                max_misfit = max_misfit + df_date["TOTAL_MISFIT"].max()
                min_misfit = min_misfit + df_date["TOTAL_MISFIT"].min()
        mean_misfit = df_misfit["TOTAL_MISFIT"].mean()

        color: Any = px.NO_COLOR
        color_discrete_map: Optional[dict] = None
        if colorby == "misfit":
            color = "TOTAL_MISFIT"
        elif colorby == "Date":
            color = "DATE"
        elif colorby == "Phases":
            color = None
            color_discrete_map = color_phases

        fig = px.bar(
            df_misfit,
            x="REAL",
            y=plot_phases,
            title=ens_name,
            range_y=[min_misfit * 0.25, max_misfit * 1.05],
            color=color,
            color_discrete_map=color_discrete_map,
            range_color=[min_misfit * 0.20, max_misfit * 1.00],
            color_continuous_scale=px.colors.sequential.amp,
        )
        if sorting:
            fig.update_layout(xaxis={"categoryorder": sorting})
        fig.update_xaxes(showticklabels=False)
        fig.update_xaxes(title_text="Realization (hover to see values)")
        fig.update_yaxes(title_text="Cumulative misfit")
        fig.add_hline(mean_misfit)
        fig.add_annotation(average_arrow_annotation(mean_misfit))
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        # fig.update_layout(coloraxis_colorbar_thickness=20)
        # fig.update(layout_coloraxis_showscale=False)

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

    return figures


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
def get_df_diff(df_smry: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with diff (sim-obs) for all data.
    Return empty dataframe if no realizations included."""

    df_diff = df_smry[["ENSEMBLE", "DATE", "REAL"]].copy()

    for col in df_smry.columns:
        if "PT:" in col:
            simvector = col
            vectortype, wellname = simvector.split(":")[0], simvector.split(":")[1]
            obsvector = vectortype + "H:" + wellname
            diff_col_name = "DIFF_" + vectortype + ":" + wellname
            df_diff[diff_col_name] = df_smry[simvector] - df_smry[obsvector]

    df_diff = df_diff.astype({"DATE": "string"})
    return df_diff


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


# --------------------------------
def average_arrow_annotation(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    decimals = 0
    if mean_value < 0.001:
        decimals = 5
    elif mean_value < 0.01:
        decimals = 4
    elif mean_value < 0.1:
        decimals = 3
    elif mean_value < 10:
        decimals = 2
    elif mean_value < 100:
        decimals = 1

    text = f"Total average: {mean_value:,.{decimals}f}"

    return {
        "x": 0.5,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": text,
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }


# --------------------------------
def _df_filter_wells(
    dframe: pd.DataFrame, wells: list, keep_wells: list
) -> pd.DataFrame:
    """Return dataframe without any of the wells not in keep_wells list"""

    # --- apply well filter
    exclude_wells = set(wells) ^ set(keep_wells)
    drop_col = []
    for col in dframe.columns:
        if ":" in col:
            for well in exclude_wells:
                if well == col.split(":")[1]:  # only drop exact matches
                    drop_col.append(col)
                    break
    return dframe.drop(drop_col, axis=1)
