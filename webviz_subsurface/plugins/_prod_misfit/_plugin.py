import logging
import time
from pathlib import Path
from .types.provider_set import (
    # create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)
from typing import Dict, List, Optional, Tuple

import dash
import pandas as pd
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
    # caching_ensemble_set_model_factory,
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
        well_collections: dict = None,
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

        logging.debug(
            f"Created presampled provider_set. "
            f"Cummulative time: {time.time() - start}"
        )

        self.ensemble_names = self._input_provider_set.names()

        self.dates = {}
        self.realizations = {}
        self.wells = {}
        self.vectors = {}
        self.phases = {}

        for ens_name in self.ensemble_names:
            logging.debug(f"Working with: {ens_name}")
            ens_provider = self._input_provider_set.provider(ens_name)
            self.realizations[ens_name] = ens_provider.realizations()
            self.dates[ens_name] = ens_provider.dates(resampling_frequency=None)

            # from wopt/wwpt/wgpt: get lists of wells, vectors and phases
            # drop wells included in user input "excl_name" lists
            (
                self.wells[ens_name],
                self.vectors[ens_name],
                self.phases[ens_name],
            ) = _get_wells_vectors_phases(
                ens_provider.vector_names(), excl_name_startswith, excl_name_contains
            )

        self.well_collections = _check_well_collections(well_collections, self.wells)

        # -----------------------------------------
        # TODO: Consider option to read hist vectors from seperate file
        # defined in config file

        # Make dataframe of hist vectors mean values (over all realizations)
        self.df_hist_mean = {}
        for ens_name in self.ensemble_names:
            hvectors = []
            for vector in self.vectors[ens_name]:
                hvectors.append(vector.split(":")[0] + "H:" + vector.split(":")[1])

            df_hist = self._input_provider_set.provider(ens_name).get_vectors_df(
                hvectors,
                None,
                None,
            )
            self.df_hist_mean[ens_name] = df_hist.groupby("DATE", as_index=False).mean()
            self.df_hist_mean[ens_name].drop(columns=["REAL"], inplace=True)
            # print(ens_name, "df_hist_mean:\n", df_hist_mean[ens_name])

        self.set_callbacks(app)

        logging.debug(f"Init done. Cummulative time: {time.time() - start}")

    @property
    def layout(self) -> wcc.Tabs:
        return main_layout(
            get_uuid=self.uuid,
            ensemble_names=self.ensemble_names,
            dates=self.dates,
            phases=self.phases,
            wells=self.wells,
            realizations=self.realizations,
            well_collections=self.well_collections,
        )

    # ---------------------------------------------
    def set_callbacks(self, app: dash.Dash) -> None:
        plugin_callbacks(
            app=app,
            get_uuid=self.uuid,
            input_provider_set=self._input_provider_set,
            ens_vectors=self.vectors,
            ens_realizations=self.realizations,
            well_collections=self.well_collections,
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


# def _get_filtered_df(
#     dframe: pd.DataFrame, excl_name_startswith: list, excl_name_contains: list
# ) -> pd.DataFrame:
#     """Remove unwanted wells/groups from dframe"""

#     drop_list = []
#     for colname in dframe.columns:
#         if ":" in colname:
#             name = colname.split(":")[1]
#             if name.startswith(tuple(excl_name_startswith)):
#                 drop_list.append(colname)
#                 continue
#             # else:
#             for excl in excl_name_contains:
#                 if excl in name:
#                     drop_list.append(colname)
#                     continue
#     if len(drop_list) > 0:
#         logging.info(f"\nDropping column keys: {drop_list}")
#     return dframe.drop(columns=drop_list)


# def _calcualte_diff_at_date(
#     df_sim: pd.DataFrame, df_hist: pd.DataFrame
# ) -> pd.DataFrame:
#     """Calculate diff (sim - obs)."""

#     date = df_sim.DATE.values[2]
#     dframe = pd.DataFrame()
#     df_sim = df_sim[df_sim.DATE == date]
#     df_hist = df_hist[df_hist.DATE == date]
#     for col in df_sim.columns:
#         if col in ["REAL", "ENSEMBLE", "DATE"]:
#             dframe[col] = df_sim[col]
#         elif col in ["WOPT", "WWPT", "WGPT", "GOPT", "GWPT", "GGPT"]:
#             vector, well = col.split(":")[0], col.split(":")[1]
#             # logging.debug(f"{vector} {well}")
#             dframe[vector + "_DIFF:" + well] = (
#                 df_sim[col] - df_hist[vector + "H:" + well].values[0]
#             )

#     return dframe


# # --------------------------------
# def get_df_stat(df_smry: pd.DataFrame) -> pd.DataFrame:
#     """Return dataframe with ensemble statistics per well across all realizations.
#     Return empty dataframe if no realizations included in df."""

#     my_ensembles = []
#     my_dates = []
#     my_wells = []
#     my_sim_vectors = []
#     my_sim_mean_values = []
#     my_sim_std_values = []
#     my_sim_p10_values = []
#     my_sim_p90_values = []
#     my_hist_values = []

#     for ens_name, dframe in df_smry.groupby("ENSEMBLE"):
#         for _date, ensdf in dframe.groupby("DATE"):

#             for col in ensdf.columns:
#                 if ":" in col:
#                     vector = col.split(":")[0]
#                     if vector in [
#                         "WOPT",
#                         "WWPT",
#                         "WGPT",
#                         "GOPT",
#                         "GWPT",
#                         "GGPT",
#                     ]:
#                         well = col.split(":")[1]
#                         my_wells.append(well)
#                         my_dates.append(_date)
#                         my_ensembles.append(ens_name)
#                         my_sim_vectors.append(vector)
#                         my_sim_mean_values.append(ensdf[col].mean())
#                         my_sim_std_values.append(ensdf[col].std())
#                         my_sim_p10_values.append(ensdf[col].quantile(0.9))
#                         my_sim_p90_values.append(ensdf[col].quantile(0.1))
#                         my_hist_values.append(ensdf[vector + "H:" + well].mean())

#     df_stat = pd.DataFrame(
#         data={
#             "ENSEMBLE": my_ensembles,
#             "WELL": my_wells,
#             "VECTOR": my_sim_vectors,
#             "DATE": my_dates,
#             "OBS": my_hist_values,
#             "SIM_MEAN": my_sim_mean_values,
#             "SIM_STD": my_sim_std_values,
#             "SIM_P10": my_sim_p10_values,
#             "SIM_P90": my_sim_p90_values,
#         }
#     )
#     df_stat = df_stat.astype({"DATE": "string"})
#     return df_stat


# # --------------------------------
# def get_df_diff_stat(df_diff: pd.DataFrame) -> pd.DataFrame:
#     """Return dataframe with ensemble statistics of production
#     difference per well across all realizations.
#     Return empty dataframe if no realizations included in df."""

#     my_ensembles = []
#     my_dates = []
#     my_wells = []
#     my_diff_vectors = []
#     my_diff_mean_values = []
#     my_diff_std_values = []
#     my_diff_p10_values = []
#     my_diff_p90_values = []

#     for ens_name, dframe in df_diff.groupby("ENSEMBLE"):
#         for _date, ensdf in dframe.groupby("DATE"):

#             for col in ensdf.columns:
#                 if ":" in col:
#                     vector = col.split(":")[0]
#                     if vector in [
#                         "DIFF_WOPT",
#                         "DIFF_WWPT",
#                         "DIFF_WGPT",
#                         "DIFF_GOPT",
#                         "DIFF_GWPT",
#                         "DIFF_GGPT",
#                     ]:
#                         well = col.split(":")[1]
#                         my_wells.append(well)
#                         my_dates.append(_date)
#                         my_ensembles.append(ens_name)
#                         my_diff_vectors.append(vector)
#                         my_diff_mean_values.append(ensdf[col].mean())
#                         my_diff_std_values.append(ensdf[col].std())
#                         my_diff_p10_values.append(ensdf[col].quantile(0.9))
#                         my_diff_p90_values.append(ensdf[col].quantile(0.1))

#     df_stat = pd.DataFrame(
#         data={
#             "ENSEMBLE": my_ensembles,
#             "WELL": my_wells,
#             "VECTOR": my_diff_vectors,
#             "DATE": my_dates,
#             "DIFF_MEAN": my_diff_mean_values,
#             "DIFF_STD": my_diff_std_values,
#             "DIFF_P10": my_diff_p10_values,
#             "DIFF_P90": my_diff_p90_values,
#         }
#     )
#     df_stat = df_stat.astype({"DATE": "string"})
#     return df_stat


# --------------------------------
def _get_wells_vectors_phases(
    vector_names: list,
    excl_name_startswith: Optional[list],
    excl_name_contains: Optional[list],
) -> Tuple[List, List, List]:
    """Return lists of wells, vectors and phases."""

    if excl_name_startswith is None:
        excl_name_startswith = []
    if excl_name_contains is None:
        excl_name_contains = []

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
        logging.debug(
            "\nWells dropped based on config excl lists:\n"
            f"{list(sorted(set(drop_list)))}"
        )

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

    logging.debug(f"\nWells: {wells}")
    logging.debug(f"\nPhases: {phases}")
    logging.debug(f"\nVectors: {vectors}")

    return wells, vectors, phases


# --------------------------------
def _check_well_collections(
    well_collections: Optional[Dict[str, List[str]]], wells: dict
) -> Dict[str, List[str]]:
    """Check well collections vs well lists.
    Any well not included in well collections is returned as Undefined."""

    all_wells = []
    for ens_wells in wells.values():
        all_wells.extend(ens_wells)
    all_wells = list(sorted(set(all_wells)))

    if well_collections is None:
        well_collections = {}
        well_collections["Undefined"] = all_wells
    else:
        undefined_wells = []
        all_collection_wells = []
        for collection_wells in well_collections.values():
            all_collection_wells.extend(collection_wells)
        all_collection_wells = set(all_collection_wells)
        for well in all_wells:
            if well not in all_collection_wells:
                undefined_wells.append(well)
        if len(undefined_wells) > 0:
            well_collections["Undefined"] = undefined_wells
            logging.warning(
                "\nWells not included in any well collection:" f"\n{undefined_wells}\n"
            )

    return well_collections
