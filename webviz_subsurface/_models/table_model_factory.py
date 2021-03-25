from typing import Dict, TypeVar, Type, Optional
from pathlib import Path
import os
import hashlib
import json
from enum import Enum

import pandas as pd
from fmu.ensemble import ScratchEnsemble

from .table_model import EnsembleTableModel
from .table_model import EnsembleTableModelSet
from .table_model_implementations import EnsembleTableModelImplArrow
from .table_model_implementations import EnsembleTableModelImplInMemDataFrame


###############################################################################
###############################################################################
"""

class WebvizRunMode(Enum):
    NON_PORTABLE = 1
    PORTABLE = 2
    BUILDING_PORTABLE = 3


# Class containing global information regarding the running webviz app instance
# For now, just referenced by WebvizFactoryRegistry, but could also be present
# in WebvizSettings if we need/want it.
# This class will be part of webviz-config
# # =============================================================================
class WebvizInstanceInfo:
    def __init__(self, run_mode: WebvizRunMode, storage_folder: Path):
        ...

    @property
    def run_mode(self) -> WebvizRunMode:
        ...

    @property
    def storage_folder(self) -> Path:
        ...


# Global registry/hub for factories that allows them to be shared between plugins
# This class is part of webviz-config is exposed through WEBVIZ_FACTORY_REGISTRY
# =============================================================================
T = TypeVar("T")


class WebvizFactoryRegistry:
    # This function will be called as part of the webviz_app.py / jinja2 template
    # factory_settings is straight from the factory_settings key in the YAML file
    def initialize(
        app_instance_info: WebvizInstanceInfo, factory_settings_dict: Dict[str, any]
    ):
        ...

    def get_factory(self, class_reference: Type[T]) -> Optional[T]:
        return None

    def set_factory(self, class_reference: Type[T], factory: T):
        ...

    def all_factory_settings() -> Dict[str, any]:
        return ""

    def app_instance_info() -> WebvizInstanceInfo:
        ...


WEBVIZ_FACTORY_REGISTRY = WebvizFactoryRegistry()

# !!!!!
# !!!!!
# Factory settings could look something like this in the YAML file:
#
# shared_settings:
#   scratch_ensembles:
#     iter-0: ../realization-*/iter-0
#     iter-1: ../realization-*/iter-1
#     iter-2: ../realization-*/iter-2
#     iter-3: ../realization-*/iter-3
#
# factory_settings:
#   EnsembleTableModelFactory:
#     backing_implementation: arrow
#     arrow_options:
#       keep_files_open: yes
#   EnsembleTimeSeriesFactory:
#     backing_implementation: parquet
#     parquet_options:
#       keep_files_open: yes
#     downcast_to_float: true
#
# pages:
#   - title: Front page
#     content:
#       - BannerImage:
#           image: ./content/reek_image.jpg
#           title: Reek FMU Webviz example
#       - Markdown:
#           markdown_file: ./content/front_page.md
#

"""
###############################################################################
###############################################################################


# =============================================================================
class EnsembleTableModelFactory:

    # -------------------------------------------------------------------------
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:

        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        print("EnsembleTableModelFactory._storage_dir:", self._storage_dir)

        if self._allow_storage_writes:
            # For now, just make sure the storage folder exists
            os.makedirs(self._storage_dir, exist_ok=True)

    ###############################################################################
    ###############################################################################
    """
    # -------------------------------------------------------------------------
    @staticmethod
    def instance() -> "EnsembleTableModelFactory":
        factory = WEBVIZ_FACTORY_REGISTRY.getFactory(EnsembleTableModelFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info()
            storage_folder = app_instance_info.storage_folder()
            allow_writes = app_instance_info.run_mode() != WebvizRunMode.PORTABLE

            # Can get settings for our factory and possibly use them when creating the factory object
            factory_options: dict = WEBVIZ_FACTORY_REGISTRY.all_factory_settings()[
                "EnsembleTableModelFactory"
            ]

            factory = EnsembleTableModelFactory(storage_folder, allow_writes)

            # Store the factory object in the registry
            WEBVIZ_FACTORY_REGISTRY.setFactory(EnsembleTableModelFactory, factory)

        return factory
    """
    ###############################################################################
    ###############################################################################

    # -------------------------------------------------------------------------
    def create_model_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> EnsembleTableModelSet:

        print("EnsembleTableModelFactory.create_model_set_from_aggregated_csv_file()")

        hashval = hashlib.md5(str(aggr_csv_file).encode()).hexdigest()
        main_storage_key = f"aggr_csv__{hashval}"

        storage_keys_to_load: Dict[str, str] = {}
        json_fn = self._storage_dir / (main_storage_key + ".json")
        try:
            with open(json_fn, "r") as file:
                storage_keys_to_load = json.load(file)
        except FileNotFoundError:
            # We can only recover from this if we're allowed to write to storage
            if not self._allow_storage_writes:
                raise

        if not storage_keys_to_load and self._allow_storage_writes:
            aggregated_df = pd.read_csv(aggr_csv_file)
            ensemble_names = aggregated_df["ENSEMBLE"].unique()

            print(f"  writing {len(ensemble_names)} ensembles to backing store")

            for ens_name in ensemble_names:
                ens_storage_key = main_storage_key + "__" + ens_name
                ensemble_df = aggregated_df[aggregated_df["ENSEMBLE"] == ens_name]
                EnsembleTableModelImplArrow.write_backing_store_from_ensemble_dataframe(
                    self._storage_dir, ens_storage_key, ensemble_df
                )
                storage_keys_to_load[ens_name] = ens_storage_key

            with open(json_fn, "w") as file:
                json.dump(storage_keys_to_load, file)

        loaded_models: Dict[str, EnsembleTableModel] = {}
        for ens_name, ens_storage_key in storage_keys_to_load.items():
            model = EnsembleTableModelImplArrow.from_backing_store(
                self._storage_dir, ens_storage_key
            )
            if model:
                loaded_models[ens_name] = model

        print(f"  loaded {len(loaded_models)} ensembles from backing store")

        num_missing_models = len(storage_keys_to_load) - len(loaded_models)
        if num_missing_models > 0:
            raise ValueError(f"Failed to load data for {num_missing_models} ensembles")

        return EnsembleTableModelSet(loaded_models)

    # -------------------------------------------------------------------------
    def create_model_set_from_per_realization_csv_file(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleTableModelSet:

        print(
            "EnsembleTableModelFactory.create_model_set_from_per_realization_csv_file()"
        )

        storage_keys_to_load: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5((ens_path + csv_file_rel_path).encode()).hexdigest()
            storage_keys_to_load[ens_name] = f"ens_csv__{hashval}"

        # We'll add all the models for the model set to this dictionary as we go
        loaded_models: Dict[str, EnsembleTableModel] = {}

        # First, try and load models from backing store
        for ens_name, ens_storage_key in dict(storage_keys_to_load).items():
            model = EnsembleTableModelImplArrow.from_backing_store(
                self._storage_dir, ens_storage_key
            )
            if model:
                loaded_models[ens_name] = model
                del storage_keys_to_load[ens_name]
                print(f"  loaded {ens_name} from backing store")

        # If there are remaining keys to load and we're allowed to write to storage,
        # we'll load the csv, write data to storage and then try and load again
        if storage_keys_to_load and self._allow_storage_writes:
            for ens_name, ens_storage_key in dict(storage_keys_to_load).items():
                ens_path = ensembles[ens_name]
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
                del scratch_ensemble

                EnsembleTableModelImplArrow.write_backing_store_from_ensemble_dataframe(
                    self._storage_dir, ens_storage_key, ensemble_df
                )
                model = EnsembleTableModelImplArrow.from_backing_store(
                    self._storage_dir, ens_storage_key
                )
                if model:
                    loaded_models[ens_name] = model
                    del storage_keys_to_load[ens_name]
                    print(f"  created and wrote {ens_name} to backing store")

        # Should not be any remaining keys
        if storage_keys_to_load:
            raise ValueError(
                f"Failed to load data for {len(storage_keys_to_load)} ensembles"
            )

        return EnsembleTableModelSet(loaded_models)


# =============================================================================
class EnsembleTableModelFactorySimpleInMemory:

    # -------------------------------------------------------------------------
    def create_model_set_from_aggregated_csv_file(
        self, aggr_csv_file: Path
    ) -> EnsembleTableModelSet:

        print(
            "EnsembleTableModelFactorySimpleInMemory.create_model_set_from_aggregated_csv_file()"
        )

        df = pd.read_csv(aggr_csv_file)
        ensemble_names = df["ENSEMBLE"].unique()

        models_dict: Dict[str, EnsembleTableModel] = {}

        for ens_name in ensemble_names:
            ensemble_df = df[df["ENSEMBLE"] == ens_name]
            model: EnsembleTableModel = EnsembleTableModelImplInMemDataFrame(
                ensemble_df
            )
            models_dict[ens_name] = model

        return EnsembleTableModelSet(models_dict)

    # -------------------------------------------------------------------------
    def create_model_set_from_per_realization_csv_file(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleTableModelSet:

        print(
            "EnsembleTableModelFactorySimpleInMemory.create_model_set_from_per_realization_csv_file()"
        )

        models_dict: Dict[str, EnsembleTableModel] = {}

        for ens_name, ens_path in ensembles.items():
            scratch_ensemble = ScratchEnsemble(ens_name, ens_path, autodiscovery=False)
            ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
            models_dict[ens_name] = EnsembleTableModelImplInMemDataFrame(ensemble_df)

        return EnsembleTableModelSet(models_dict)
