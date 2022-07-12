# pylint: disable=too-many-arguments
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._models import WellAttributesModel
from webviz_subsurface._providers import Frequency

from .._simulation_time_series.types.provider_set import (
    create_presampled_provider_set_from_paths,
)
from ._plugin_ids import PluginIds
from .shared_settings import Filter
from .views import MisfitPerRealView

#from ._callbacks import plugin_callbacks
#from ._layout import main_layout


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
    * **`sampling`:** Frequency for the data sampling.
    * **`well_attributes_file`:** Path to json file containing info of well attributes.
    The attribute category values can be used for filtering of well collections.
    * **`excl_name_startswith`:** Exclude wells that starts with this string.
    * **`excl_name_endswith`:** Exclude wells that ends with this string.
    * **`excl_name_contains`:** Exclude wells that contains this string.
    * **`phase_weights`:** Dict of "Oil", "Water" and "Gas" inverse weight factors that
    are included as weight option for misfit per real calculation.
    ---

    **Summary data**

    This plugin needs the following summary vectors to be stored with arrow format:
    * WOPT+WOPTH and/or WWPT+WWPTH and/or WGPT+WGPTH

    Summary files can be converted to arrow format with the `ECL2CSV` forward model.


    `well_attributes_file`: Optional json file with well attributes.
    The file needs to follow the format below. The categorical attributes \
    are completely flexible (user defined).
    ```json
    {
        "version" : "0.1",
        "wells" : [
        {
            "alias" : {
                "eclipse" : "A1"
            },
            "attributes" : {
                "structure" : "East",
                "welltype" : "producer"
            },
            "name" : "55_33-A-1"
        },
        {
            "alias" : {
                "eclipse" : "A5"
            },
            "attributes" : {
                "structure" : "North",
                "welltype" : "injector"
            },
            "name" : "55_33-A-5"
        },
        ]
    }
    ```
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        sampling: str = Frequency.YEARLY.value,
        well_attributes_file: str = None,
        excl_name_startswith: list = None,
        excl_name_endswith: list = None,
        excl_name_contains: list = None,
        phase_weights: dict = None,
    ):

        super().__init__()

        if phase_weights is None:
            phase_weights = {"Oil": 1.0, "Water": 1.0, "Gas": 300.0}
        self.weight_reduction_factor_oil = phase_weights["Oil"]
        self.weight_reduction_factor_wat = phase_weights["Water"]
        self.weight_reduction_factor_gas = phase_weights["Gas"]

        if excl_name_startswith is None:
            excl_name_startswith = []
        excl_name_startswith = [str(element) for element in excl_name_startswith]
        if excl_name_endswith is None:
            excl_name_endswith = []
        excl_name_endswith = [str(element) for element in excl_name_endswith]
        if excl_name_contains is None:
            excl_name_contains = []
        excl_name_contains = [str(element) for element in excl_name_contains]

        # Must define valid frequency
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

        logging.debug("Created presampled provider_set.")

        self.ensemble_names = self._input_provider_set.names()

        self.dates = {}
        self.realizations = {}
        self.wells = {}
        self.vectors = {}
        self.phases = {}

        self._well_attributes = (
            WellAttributesModel(
                self.ensemble_names[0],
                ensemble_paths[self.ensemble_names[0]],
                well_attributes_file,
            )
            if well_attributes_file is not None
            else None
        )

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
                ens_provider.vector_names(),
                excl_name_startswith,
                excl_name_endswith,
                excl_name_contains,
            )

        # self.well_collections = _get_well_collections_from_attr(well_attrs, self.wells)
        self.well_collections = _get_well_collections_from_attr(
            self.wells, self._well_attributes
        )
#-----------------------------------------------------------------------------------------------
        #some calculations
        self.all_dates, self.all_phases, self.all_wells, self.all_realizations = [], [], [], []
        for ens_name in self.ensemble_names:
            self.all_dates.extend(self.dates[ens_name])
            self.all_phases.extend(self.phases[ens_name])
            self.all_wells.extend(self.wells[ens_name])
            self.all_realizations.extend(self.realizations[ens_name])
        self.all_dates = list(sorted(set(self.all_dates)))
        self.all_phases = list(sorted(set(self.all_phases)))
        self.all_wells = list(sorted(set(self.all_wells)))
        self.all_realizations = list(sorted(set(self.all_realizations)))
        self.all_well_collection_names = []
        for collection_name in self.well_collections.keys():
            self.all_well_collection_names.append(collection_name)
#-----------------------------------------------------------------------------------------------
        #add views, settings and stores

        self.add_store(
            PluginIds.Stores.SELECTED_ENSEMBLES, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_DATES, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_PHASE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_WELLS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_COMBINE_WELLS_COLLECTION, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_WELL_COLLECTIONS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_REALIZATIONS, WebvizPluginABC.StorageType.SESSION
        )

        self.add_shared_settings_group(Filter(self.ensemble_names,
            self.all_dates,
            self.all_phases,
            self.all_wells,
            self.all_realizations,
            self.all_well_collection_names), PluginIds.SharedSettings.FILTER)

        self.add_view(MisfitPerRealView(),PluginIds.MisfitViews.PRODUCTION_MISFIT_PER_REAL)

    
    @property
    def layout(self):
        return

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return (
            [self._well_attributes.webviz_store]
            if self._well_attributes is not None
            else []
        )

    # ---------------------------------------------


# ------------------------------------------------------------------------
# support functions below here
# ------------------------------------------------------------------------

# ---------------------------
def _get_wells_vectors_phases(
    vector_names: List[str],
    excl_name_startswith: List[str],
    excl_name_endswith: List[str],
    excl_name_contains: List[str],
) -> Tuple[List, List, List]:
    """Return lists of wells, vectors and phases."""

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

        if _skip_well(
            well, excl_name_startswith, excl_name_endswith, excl_name_contains
        ):
            drop_list.append(well)
            continue

        if well not in wells:
            wells.append(well)
        if vector not in vectors:
            vectors.append(vector)

    wells, vectors = sorted(wells), sorted(vectors)

    if not vectors:
        RuntimeError("No WOPT, WWPT or WGPT vectors found.")

    if drop_list:
        logging.debug(
            "\nWells dropped based on config excl lists:\n"
            f"{list(sorted(set(drop_list)))}"
        )

    logging.debug(f"\nWells: {wells}")
    logging.debug(f"\nPhases: {phases}")
    logging.debug(f"\nVectors: {vectors}")

    return wells, vectors, list(phases)


def _skip_well(
    well: str,
    excl_name_startswith: List[str],
    excl_name_endswith: List[str],
    excl_name_contains: List[str],
) -> bool:
    """Check well name against exclude strings and return True if it should be skipped."""

    if well.startswith(tuple(excl_name_startswith)):
        return True
    if well.endswith(tuple(excl_name_endswith)):
        return True
    for excl in excl_name_contains:
        if excl in well:
            return True
    return False


# --------------------------------
def _get_well_collections_from_attr(
    wells: dict,
    well_attributes: Optional[WellAttributesModel],
) -> Dict[str, List[str]]:
    """Create well_collections dictionary. Then check
    well collections vs well lists. Any well not included in well collections is
    returned as Undefined."""

    all_wells = []
    for ens_wells in wells.values():
        all_wells.extend(ens_wells)
    all_wells = list(sorted(set(all_wells)))

    well_collections = {}

    if well_attributes is None:
        well_collections["Undefined"] = all_wells
        return well_collections

    # create well_collections dictionary from dataframe
    df_well_groups = well_attributes.dataframe_melted.dropna()
    df_cols = df_well_groups.columns
    if "WELL" not in df_cols or "VALUE" not in df_cols:
        RuntimeError(
            f"The {well_attributes.file_name} file must contain the columns"
            " 'WELL' and 'VALUE'"
        )
    for group in df_well_groups.groupby("VALUE"):
        well_collections[group[0]] = sorted(list(set(group[1].WELL.to_list())))

    undefined_wells = []
    all_collection_wells = []

    for collection_wells in well_collections.values():
        all_collection_wells.extend(collection_wells)
    all_collection_wells = list(set(all_collection_wells))
    undefined_wells = [well for well in all_wells if well not in all_collection_wells]
    if undefined_wells:
        well_collections["Undefined"] = undefined_wells
        logging.warning(
            "\nWells not included in any well collection ('Undefined'):"
            f"\n{undefined_wells}\n"
            f"Update the {well_attributes.file_name} file if they should be included"
        )

    return well_collections