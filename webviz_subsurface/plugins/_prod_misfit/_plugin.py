import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dash
import pandas as pd
import webviz_core_components as wcc

# import webviz_subsurface_components as wsc
from dash import Input, Output  # , html  # Dash, State, dcc,

# from dash.exceptions import PreventUpdate
from fmu import ensemble

# from plotly.subplots import make_subplots
from webviz_config import WebvizPluginABC, WebvizSettings  # EncodedFile,
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._models import (  # caching_ensemble_set_model_factory,
    EnsembleSetModel,
)
from webviz_subsurface._providers import Frequency

from ._callbacks import plugin_callbacks
from ._layout import main_layout
from .types.provider_set import (  # create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)


class ProdMisfit(WebvizPluginABC):
    """Visualizes production data misfit at selected date.

    When not dealing with absolute value of differences, difference plots are
    represented as: (simulated - observed),
    i.e. negative values means sim is lower than obs and vice versa.

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
            ensemble_paths, "share/results/unsmry/*.arrow", self._sampling
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
                elif vector_type == "WWPT":
                    wat_phase = True
                elif vector_type == "WGPT":
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
