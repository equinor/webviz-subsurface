# pylint: disable=too-many-arguments
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dash
import pandas as pd
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers import Frequency

from ._callbacks import plugin_callbacks
from ._layout import main_layout
from .types.provider_set import create_presampled_provider_set_from_paths


class ProdMisfit(WebvizPluginABC):
    """Visualizes production data misfit at selected date(s).

    When not dealing with absolute value of differences, difference plots are
    represented as: (simulated - observed),
    i.e. negative values means sim is lower than obs and vice versa.

    **Features**
    * Visualization of prod misfit at selected time.
    * Visualization of prod coverage at selected time.
    * Heatmap representation of ensemble mean misfit for selected dates.

    ---
    * **`ensembles`:** Which ensembles in `shared_settings` to include.
    * **`rel_file_pattern`:** path to `.arrow` files with summary data.
    * **`gruptree_file`:** `.csv` with gruptree information.
    * **`sampling`:** Frequency for the data sampling.
    * **`excl_name_startswith`:** Filter out wells that starts with this string
    * **`excl_name_contains`:** Filter out wells that contains this string
    * **`phase_weights`:** Dict of "Oil", "Water" and "Gas" (inverse) weight factors that
    are included as weight option for misfit per real calculation.
    * **`well_groups_file`:** Path to csv file containing info of well name and its
    corresponding group name. Must contain the column names 'PARENT' and 'CHILD'.
    ---

    **Summary data**

    This plugin needs the following summary vectors to be stored with arrow format:
    * WOPT+WOPTH and/or WWPT+WWPTH and/or WGPT+WGPTH

    Summary files can be converted to arrow format with the `ECL2CSV` forward model.
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        sampling: str = Frequency.YEARLY.value,  # "yearly"
        # sampling: Union[str, list] # make it possible to add user specified date list?
        excl_name_startswith: list = None,
        excl_name_contains: list = None,
        phase_weights: dict = None,
        well_groups_file: str = None,
    ):

        super().__init__()

        start = time.time()

        if phase_weights is None:
            phase_weights = {"Oil": 1.0, "Water": 1.0, "Gas": 300.0}
        self.weight_reduction_factor_oil = phase_weights["Oil"]
        self.weight_reduction_factor_wat = phase_weights["Water"]
        self.weight_reduction_factor_gas = phase_weights["Gas"]

        # Must define valid freqency
        self._sampling = Frequency(sampling)

        ensemble_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        self._input_provider_set = create_presampled_provider_set_from_paths(
            ensemble_paths, rel_file_pattern, self._sampling
        )

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

        self.well_collections = _get_well_collections(well_groups_file, self.wells)

        # -----------------------------------------
        # TODO: Consider option to read hist vectors from seperate file
        # defined in config file

        # # Make dataframe of hist vectors mean values (over all realizations)
        # self.df_hist_mean = {}
        # for ens_name in self.ensemble_names:
        #     hvectors = []
        #     for vector in self.vectors[ens_name]:
        #         hvectors.append(vector.split(":")[0] + "H:" + vector.split(":")[1])

        #     df_hist = self._input_provider_set.provider(ens_name).get_vectors_df(
        #         hvectors,
        #         None,
        #         None,
        #     )
        #     self.df_hist_mean[ens_name] = df_hist.groupby("DATE", as_index=False).mean()
        #     self.df_hist_mean[ens_name].drop(columns=["REAL"], inplace=True)
        #     # print(ens_name, "df_hist_mean:\n", self.df_hist_mean[ens_name])

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


# ------------------------------------------------------------------------
# support functions below here
# ------------------------------------------------------------------------


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
        all_collection_wells = list(set(all_collection_wells))
        for well in all_wells:
            if well not in all_collection_wells:
                undefined_wells.append(well)
        if len(undefined_wells) > 0:
            well_collections["Undefined"] = undefined_wells
            logging.warning(
                "\nWells not included in any well collection ('Undefined'):"
                f"\n{undefined_wells}\n"
            )

    return well_collections


# --------------------------------
def _get_well_collections(
    well_groups_file: Optional[str], wells: dict
) -> Dict[str, List[str]]:
    """Read csv file and create well_collections dictionary. Then check well collections
    vs well lists. Any well not included in well collections is returned as Undefined."""

    all_wells = []
    for ens_wells in wells.values():
        all_wells.extend(ens_wells)
    all_wells = list(sorted(set(all_wells)))

    well_collections = {}

    if well_groups_file is None:
        well_collections["Undefined"] = all_wells
    else:

        # create well_collections dictionary from csv file
        df_well_groups = pd.read_csv(well_groups_file).dropna()
        df_cols = df_well_groups.columns
        if "PARENT" not in df_cols or "CHILD" not in df_cols:
            RuntimeError(
                "If included, the csv file 'well_groups_file' must contain the columns"
                " 'PARENT' and 'CHILD'"
            )
        if "KEYWORD" in df_cols:
            df_well_groups = df_well_groups[df_well_groups["KEYWORD"] == "WELSPECS"]
        for group in df_well_groups.groupby("PARENT"):
            well_collections[group[0]] = sorted(list(set(group[1].CHILD.to_list())))

        undefined_wells = []
        all_collection_wells = []

        for collection_wells in well_collections.values():
            all_collection_wells.extend(collection_wells)
        all_collection_wells = list(set(all_collection_wells))
        for well in all_wells:
            if well not in all_collection_wells:
                undefined_wells.append(well)
        if len(undefined_wells) > 0:
            well_collections["Undefined"] = undefined_wells
            logging.warning(
                "\nWells not included in any well collection ('Undefined'):"
                f"\n{undefined_wells}\n"
            )

    return well_collections


# ---------------------------
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

    wells, vectors, drop_list = [], [], []
    phases = set()

    for vector in vector_names:
        if vector.startswith("WOPT:"):
            phases.add("Oil")
        elif vector.startswith("WWPT:"):
            phases.add("Water")
        elif vector.startswith("WGPT:"):
            phases.add("Gas")
        else:
            continue

        well = vector.split(":")[1]
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

    wells, vectors = sorted(wells), sorted(vectors)

    if len(vectors) == 0:
        RuntimeError("No WOPT, WWPT or WGPT vectors found.")

    if len(drop_list) > 0:
        logging.debug(
            "\nWells dropped based on config excl lists:\n"
            f"{list(sorted(set(drop_list)))}"
        )

    logging.debug(f"\nWells: {wells}")
    logging.debug(f"\nPhases: {phases}")
    logging.debug(f"\nVectors: {vectors}")

    return wells, vectors, list(phases)
