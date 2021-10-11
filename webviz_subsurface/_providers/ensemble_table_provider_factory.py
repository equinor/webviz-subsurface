import hashlib
import json
import logging
import os
import pickle  # nosec
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from fmu.ensemble import ScratchEnsemble
from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from .._utils.perf_timer import PerfTimer
from .ensemble_table_provider import EnsembleTableProvider, EnsembleTableProviderSet
from .ensemble_table_provider_impl_arrow import EnsembleTableProviderImplArrow
from .ensemble_table_provider_impl_inmem_parquet import (
    EnsembleTableProviderImplInMemParquet,
)


class BackingType(Enum):
    ARROW = "arrow"
    INMEM_PARQUET = "inmem_parquet"


LOGGER = logging.getLogger(__name__)


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec


class EnsembleTableProviderFactory(WebvizFactory):
    def __init__(
        self,
        root_storage_folder: Path,
        backing_type: BackingType,
        allow_storage_writes: bool,
    ) -> None:

        self._storage_dir = Path(root_storage_folder) / __name__
        self._backing_type: BackingType = backing_type
        self._allow_storage_writes = allow_storage_writes
        self._scratch_ensemble_cache: Dict[str, bytes] = {}

        LOGGER.info(
            f"EnsembleTableProviderFactory init: backing_type={repr(self._backing_type)}"
        )
        LOGGER.info(
            f"EnsembleTableProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            # For now, just make sure the storage folder exists
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsembleTableProviderFactory":
        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleTableProviderFactory)

        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            backing_type = BackingType.ARROW
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            my_settings = WEBVIZ_FACTORY_REGISTRY.all_factory_settings.get(
                "EnsembleTableProviderFactory"
            )
            if my_settings:
                LOGGER.info(
                    f"Parsing settings for EnsembleTableProviderFactory: {my_settings}"
                )
                if "backing_type" in my_settings:
                    backing_type = BackingType(my_settings["backing_type"])

            factory = EnsembleTableProviderFactory(
                storage_folder, backing_type, allow_writes
            )
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleTableProviderFactory, factory)

        return factory

    def cleanup_resources_after_plugin_init(self) -> None:
        self._scratch_ensemble_cache.clear()

    def create_provider_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> EnsembleTableProviderSet:

        LOGGER.info(f"create_provider_set_from_aggregated_csv_file() - {aggr_csv_file}")

        hashval = _make_hash_string(str(aggr_csv_file))
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
                f"Saving {len(ensemble_names)} table providers from aggregated CSV to backing store"
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

        num_missing_models = len(storage_keys_to_load) - len(created_providers)
        if num_missing_models > 0:
            raise ValueError(f"Failed to load data for {num_missing_models} ensembles")

        LOGGER.info(f"Loaded {len(created_providers)} providers from backing store")

        return EnsembleTableProviderSet(created_providers)

    def create_provider_set_from_per_realization_csv_file(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleTableProviderSet:
        # pylint: disable=too-many-locals

        LOGGER.info(
            f"create_provider_set_from_per_realization_csv_file() - {csv_file_rel_path}"
        )
        timer = PerfTimer()

        # Try and create/load providers from backing store
        created_providers: Dict[str, EnsembleTableProvider] = {}
        missing_storage_keys: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = _make_hash_string(ens_path + csv_file_rel_path)
            storage_key = f"ens_csv__{hashval}"
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(f"Loaded table provider for {ens_name} from backing store")
            else:
                missing_storage_keys[ens_name] = storage_key

        # If there are remaining keys AND we're allowed to write to storage,
        # we'll load the csv, write data to storage and then try and load again
        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, storage_key in dict(missing_storage_keys).items():
                timer.lap_s()
                ens_path = ensembles[ens_name]
                scratch_ensemble = self._get_or_create_scratch_ensemble(
                    ens_name, ens_path
                )
                elapsed_create_scratch_ens_s = timer.lap_s()

                ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
                del scratch_ensemble
                elapsed_load_csv_s = timer.lap_s()

                self._write_data_to_backing_store(storage_key, ensemble_df)
                provider = self._create_provider_instance_from_backing_store(
                    storage_key
                )
                elapsed_write_s = timer.lap_s()

                if provider:
                    created_providers[ens_name] = provider
                    del missing_storage_keys[ens_name]
                    LOGGER.info(
                        f"Saved table provider for {ens_name} to backing store ("
                        f"create_scratch_ens={elapsed_create_scratch_ens_s:.2f}s "
                        f"load_csv={elapsed_load_csv_s:.2f}s "
                        f"write={elapsed_write_s:.2f}s)"
                    )

        if missing_storage_keys:
            raise ValueError(
                f"Failed to load/create provider(s) for {len(missing_storage_keys)} ensembles"
            )

        LOGGER.info(
            f"create_provider_set_from_per_realization_csv_file() "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleTableProviderSet(created_providers)

    # Function to load the parameters.txt/json file using fmu.ensemble.
    # Should this be a separate Factory class? Typically both csv files and
    # the parameter file will be loaded from the same ensemble. Currently the ensembles
    # will be loaded and deleted twice if that is the case...
    def create_provider_set_from_per_realization_parameter_file(
        self, ensembles: Dict[str, str]
    ) -> EnsembleTableProviderSet:

        LOGGER.info("create_provider_set_from_per_realization_parameter_file() ...")

        timer = PerfTimer()

        storage_keys_to_load: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = _make_hash_string(ens_path + "parameters")
            storage_keys_to_load[ens_name] = f"parameters__{hashval}"

        # We'll add all the models for the model set to this dictionary as we go
        created_providers: Dict[str, EnsembleTableProvider] = {}

        # First, try and load models from backing store
        for ens_name, storage_key in dict(storage_keys_to_load).items():
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider
                del storage_keys_to_load[ens_name]
                LOGGER.info(f"Loaded table provider for {ens_name} from backing store")

        # If there are remaining keys to load and we're allowed to write to storage,
        # we'll load the parameters file, write data to storage and then try and load again
        if storage_keys_to_load and self._allow_storage_writes:
            for ens_name, storage_key in dict(storage_keys_to_load).items():
                timer.lap_s()
                ens_path = ensembles[ens_name]
                scratch_ensemble = self._get_or_create_scratch_ensemble(
                    ens_name, ens_path
                )
                elapsed_create_scratch_ens_s = timer.lap_s()

                ensemble_df = scratch_ensemble.parameters
                del scratch_ensemble
                elapsed_load_parameters_s = timer.lap_s()

                self._write_data_to_backing_store(storage_key, ensemble_df)
                provider = self._create_provider_instance_from_backing_store(
                    storage_key
                )
                elapsed_write_s = timer.lap_s()

                if provider:
                    created_providers[ens_name] = provider
                    del storage_keys_to_load[ens_name]
                    LOGGER.info(
                        f"Saved table provider for {ens_name} to backing store ("
                        f"create_scratch_ens={elapsed_create_scratch_ens_s:.2f}s "
                        f"load_parameters={elapsed_load_parameters_s:.2f}s "
                        f"write={elapsed_write_s:.2f}s)"
                    )

        # Should not be any remaining keys
        if storage_keys_to_load:
            raise ValueError(
                f"Failed to load data for {len(storage_keys_to_load)} ensembles"
            )

        LOGGER.info(
            f"create_provider_set_from_per_realization_parameter_file() "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleTableProviderSet(created_providers)

    def _create_provider_instance_from_backing_store(
        self, storage_key: str
    ) -> Optional[EnsembleTableProvider]:
        if self._backing_type == BackingType.ARROW:
            return EnsembleTableProviderImplArrow.from_backing_store(
                self._storage_dir, storage_key
            )
        if self._backing_type == BackingType.INMEM_PARQUET:
            return EnsembleTableProviderImplInMemParquet.from_backing_store(
                self._storage_dir, storage_key
            )

        raise ValueError("Unhandled backing type")

    def _write_data_to_backing_store(
        self, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:
        if self._backing_type == BackingType.ARROW:
            EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )
        elif self._backing_type == BackingType.INMEM_PARQUET:
            EnsembleTableProviderImplInMemParquet.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )
        else:
            raise ValueError("Unhandled backing type")

    def _get_or_create_scratch_ensemble(
        self, ens_name: str, ens_path: str
    ) -> ScratchEnsemble:
        """Either creates a new ScratchEnsemble or retrieves a previously created one
        from our internal cache. Note that we cache a pickled version of ScratchEnsembles
        to avoid memory bloating as data is loaded and internalized by the ensemble
        """
        key = json.dumps({"ens_name": ens_name, "ens_path": ens_path})
        if key in self._scratch_ensemble_cache:
            return pickle.loads(self._scratch_ensemble_cache[key])  # nosec

        scratch_ensemble = ScratchEnsemble(ens_name, ens_path).filter("OK")
        self._scratch_ensemble_cache[key] = pickle.dumps(
            scratch_ensemble, pickle.HIGHEST_PROTOCOL
        )

        return scratch_ensemble
