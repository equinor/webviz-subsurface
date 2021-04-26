from typing import Dict
from pathlib import Path
import os
import hashlib
import json
from enum import Enum

import pandas as pd
from fmu.ensemble import ScratchEnsemble

# Use this code when WEBVIZ_FACTORY_REGISTRY is merged into webviz-config
# from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
# from webviz_config.webviz_instance_info import WebvizRunMode

from .table_model import EnsembleTableModel
from .table_model import EnsembleTableModelSet
from .table_model_implementations import EnsembleTableModelImplArrow
from .table_model_implementations import EnsembleTableModelImplInMemDataFrame


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

    # -------------------------------------------------------------------------
    """
    @staticmethod
    def instance() -> "EnsembleTableModelFactory":
        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleTableModelFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            # Can get settings for our factory and possibly use them
            # when creating the factory object
            my_factory_settings = WEBVIZ_FACTORY_REGISTRY.all_factory_settings.get(
                "EnsembleTableModelFactory"
            )

            factory = EnsembleTableModelFactory(storage_folder, allow_writes)
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleTableModelFactory, factory)

        return factory
    """

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

    # Function to load the parameters.txt/json file using fmu.ensemble.
    # Should this be a separate Factory class? Typically both csv files and
    # the parameter file will be loaded from the same ensemble. Currently the ensembles
    # will be loaded and deleted twice if that is the case...
    # -------------------------------------------------------------------------
    def create_model_set_from_per_parameter_file(
        self, ensembles: Dict[str, str]
    ) -> EnsembleTableModelSet:

        print("EnsembleTableModelFactory.create_model_set_from_per_parameter_file()")

        storage_keys_to_load: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5((ens_path + "parameters").encode()).hexdigest()
            storage_keys_to_load[ens_name] = f"parameters__{hashval}"

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
        # we'll load the parameters file, write data to storage and then try and load again
        if storage_keys_to_load and self._allow_storage_writes:
            for ens_name, ens_storage_key in dict(storage_keys_to_load).items():
                ens_path = ensembles[ens_name]
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                ensemble_df = scratch_ensemble.parameters
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
