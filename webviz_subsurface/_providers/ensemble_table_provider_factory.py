from typing import Dict, Optional
from pathlib import Path
import os
import hashlib
import json
from enum import Enum
import logging

import pandas as pd
from fmu.ensemble import ScratchEnsemble

# Use this code when WEBVIZ_FACTORY_REGISTRY is merged into webviz-config
# from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
# from webviz_config.webviz_instance_info import WebvizRunMode

from .ensemble_table_provider import EnsembleTableProvider
from .ensemble_table_provider import EnsembleTableProviderSet
from .ensemble_table_provider_impl_arrow import EnsembleTableProviderImplArrow

# from .ensemble_table_provider_impl_inmem_parquet import (
#    EnsembleTableProviderImplInMemParquet,
# )

LOGGER = logging.getLogger(__name__)


# =============================================================================
class EnsembleTableProviderFactory:

    # -------------------------------------------------------------------------
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:

        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        LOGGER.info(
            f"EnsembleTableProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            # For now, just make sure the storage folder exists
            os.makedirs(self._storage_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    """
    @staticmethod
    def instance() -> "EnsembleTableProvider":
        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleTableProvider)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            # Can get settings for our factory and possibly use them
            # when creating the factory object
            my_factory_settings = WEBVIZ_FACTORY_REGISTRY.all_factory_settings.get(
                "EnsembleTableProvider"
            )

            factory = EnsembleTableProviderFactory(storage_folder, allow_writes)
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleTableProviderFactory, factory)

        return factory
    """

    # -------------------------------------------------------------------------
    def create_provider_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> EnsembleTableProviderSet:

        LOGGER.info(
            "EnsembleTableProviderFactory.create_provider_set_from_aggregated_csv_file()..."
        )

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

            LOGGER.info(
                f"EnsembleTableProviderFactory: writing {len(ensemble_names)} providers from aggregated CSV file to backing store"
            )

            for ens_name in ensemble_names:
                storage_key = main_storage_key + "__" + ens_name
                ensemble_df = aggregated_df[aggregated_df["ENSEMBLE"] == ens_name]
                self._write_data_to_backing_store(storage_key, ensemble_df)
                storage_keys_to_load[ens_name] = storage_key

            with open(json_fn, "w") as file:
                json.dump(storage_keys_to_load, file)

        created_providers: Dict[str, EnsembleTableProvider] = {}
        for ens_name, storage_key in storage_keys_to_load.items():
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider

        LOGGER.info(
            f"EnsembleTableProviderFactory: created/loaded {len(created_providers)} providers from backing store"
        )

        num_missing_models = len(storage_keys_to_load) - len(created_providers)
        if num_missing_models > 0:
            raise ValueError(f"Failed to load data for {num_missing_models} ensembles")

        return EnsembleTableProviderSet(created_providers)

    # -------------------------------------------------------------------------
    def create_provider_set_from_per_realization_csv_file(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleTableProviderSet:

        LOGGER.info(
            "EnsembleTableProviderFactory.create_provider_set_from_per_realization_csv_file()..."
        )

        # Try and create/load providers from backing store
        created_providers: Dict[str, EnsembleTableProvider] = {}
        missing_storage_keys: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5((ens_path + csv_file_rel_path).encode()).hexdigest()
            storage_key = f"ens_csv__{hashval}"
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(
                    f"EnsembleTableProviderFactory: created/loaded provider for {ens_name} from backing store"
                )
            else:
                missing_storage_keys[ens_name] = storage_key

        # If there are remaining keys AND we're allowed to write to storage,
        # we'll load the csv, write data to storage and then try and load again
        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, storage_key in dict(missing_storage_keys).items():
                ens_path = ensembles[ens_name]
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
                del scratch_ensemble

                self._write_data_to_backing_store(storage_key, ensemble_df)
                provider = self._create_provider_instance_from_backing_store(
                    storage_key
                )
                if provider:
                    created_providers[ens_name] = provider
                    del missing_storage_keys[ens_name]
                    LOGGER.info(
                        f"EnsembleTableProviderFactory: wrote/created provider for {ens_name} to backing store"
                    )

        if missing_storage_keys:
            raise ValueError(
                f"Failed to create provider(s) for {len(missing_storage_keys)} ensembles"
            )

        return EnsembleTableProviderSet(created_providers)

    # Function to load the parameters.txt/json file using fmu.ensemble.
    # Should this be a separate Factory class? Typically both csv files and
    # the parameter file will be loaded from the same ensemble. Currently the ensembles
    # will be loaded and deleted twice if that is the case...
    # -------------------------------------------------------------------------
    def create_provider_set_from_per_realization_parameter_file(
        self, ensembles: Dict[str, str]
    ) -> EnsembleTableProviderSet:

        print(
            "EnsembleTableProviderFactory.create_provider_set_from_per_realization_parameter_file()"
        )

        storage_keys_to_load: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5((ens_path + "parameters").encode()).hexdigest()
            storage_keys_to_load[ens_name] = f"parameters__{hashval}"

        # We'll add all the models for the model set to this dictionary as we go
        created_providers: Dict[str, EnsembleTableProvider] = {}

        # First, try and load models from backing store
        for ens_name, storage_key in dict(storage_keys_to_load).items():
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider
                del storage_keys_to_load[ens_name]
                print(f"  loaded {ens_name} from backing store")

        # If there are remaining keys to load and we're allowed to write to storage,
        # we'll load the parameters file, write data to storage and then try and load again
        if storage_keys_to_load and self._allow_storage_writes:
            for ens_name, storage_key in dict(storage_keys_to_load).items():
                ens_path = ensembles[ens_name]
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                ensemble_df = scratch_ensemble.parameters
                del scratch_ensemble

                self._write_data_to_backing_store(storage_key, ensemble_df)
                provider = self._create_provider_instance_from_backing_store(
                    storage_key
                )
                if provider:
                    created_providers[ens_name] = provider
                    del storage_keys_to_load[ens_name]
                    print(f"  created and wrote {ens_name} to backing store")

        # Should not be any remaining keys
        if storage_keys_to_load:
            raise ValueError(
                f"Failed to load data for {len(storage_keys_to_load)} ensembles"
            )

        return EnsembleTableProviderSet(created_providers)

    # -------------------------------------------------------------------------
    def _create_provider_instance_from_backing_store(
        self, storage_key: str
    ) -> Optional[EnsembleTableProvider]:
        return EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )

    # -------------------------------------------------------------------------
    def _write_data_to_backing_store(
        self, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:
        EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
            self._storage_dir, storage_key, ensemble_df
        )
