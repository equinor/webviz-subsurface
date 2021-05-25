from typing import List, Dict, Optional
from pathlib import Path
import os
import hashlib
import json
from enum import Enum
import logging

import pandas as pd
from fmu.ensemble import ScratchEnsemble

from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_instance_info import WebvizRunMode

from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_set import EnsembleSummaryProviderSet
from .ensemble_summary_provider_impl_arrow import EnsembleSummaryProviderImplArrow
from .ensemble_summary_provider_impl_parquet import EnsembleSummaryProviderImplParquet
from .ensemble_summary_provider_impl_inmem_parquet import (
    EnsembleSummaryProviderImplInMemParquet,
)
from .._utils.perf_timer import PerfTimer


class BackingType(Enum):
    ARROW = 1
    ARROW_PER_REAL_SMRY_IMPORT_EXPERIMENTAL = 2
    PARQUET = 3
    INMEM_PARQUET = 4


LOGGER = logging.getLogger(__name__)


# =============================================================================
class EnsembleSummaryProviderFactory(WebvizFactory):

    # -------------------------------------------------------------------------
    def __init__(self, root_storage_folder: Path, backing_type: BackingType) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._backing_type: BackingType = backing_type
        self._allow_storage_writes = True

        LOGGER.info(
            f"EnsembleSummaryProviderFactory init: backing_type={repr(self._backing_type)}"
        )
        LOGGER.info(
            f"EnsembleSummaryProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    @staticmethod
    def instance() -> "EnsembleSummaryProviderFactory":
        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleSummaryProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder

            factory = EnsembleSummaryProviderFactory(storage_folder, BackingType.ARROW)

            # Store the factory object in the registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleSummaryProviderFactory, factory)

        return factory

    # -------------------------------------------------------------------------
    def create_provider_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> EnsembleSummaryProviderSet:

        LOGGER.info(
            f"create_provider_set_from_aggregated_csv_file() starting - {aggr_csv_file}"
        )
        timer = PerfTimer()

        hashval = hashlib.md5(str(aggr_csv_file).encode()).hexdigest()
        main_storage_key = f"aggr_csv__{hashval}"

        # Since our only input is the file name of a single aggregated CSV file, we rely
        # on reading the dict which maps from ensemble names to the keys that need to
        # be loaded from a JSON file on disk.
        storage_keys_to_load: Dict[str, str] = {}
        json_filename = self._storage_dir / (main_storage_key + ".json")
        try:
            with open(json_filename, "r") as file:
                storage_keys_to_load = json.load(file)
        except FileNotFoundError:
            # No dict found on disk. We can only recover from this if we're allowed to
            # write to storage. In that case we'll import the CSV file and write the
            # resulting dict to JSON further down
            if not self._allow_storage_writes:
                raise

        # Possibly do import of CSV and writing of provider data to backing store
        if not storage_keys_to_load and self._allow_storage_writes:
            aggregated_df = pd.read_csv(aggr_csv_file)
            ensemble_names = aggregated_df["ENSEMBLE"].unique()

            LOGGER.info(
                f"Saving {len(ensemble_names)} "
                f"summary providers from aggregated CSV to backing store"
            )

            for ens_name in ensemble_names:
                storage_key = main_storage_key + "__" + ens_name
                ensemble_df = aggregated_df[aggregated_df["ENSEMBLE"] == ens_name]
                self._write_data_to_backing_store(storage_key, ensemble_df.copy())
                storage_keys_to_load[ens_name] = storage_key

            with open(json_filename, "w") as file:
                json.dump(storage_keys_to_load, file)

        created_providers: Dict[str, EnsembleSummaryProvider] = {}
        for ens_name, storage_key in storage_keys_to_load.items():
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider

        num_missing_models = len(storage_keys_to_load) - len(created_providers)
        if num_missing_models > 0:
            raise ValueError(f"Failed to load data for {num_missing_models} ensembles")

        LOGGER.info(f"Loaded {len(created_providers)} providers from backing store")

        LOGGER.info(
            f"create_provider_set_from_aggregated_csv_file() finished "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleSummaryProviderSet(created_providers)

    # -------------------------------------------------------------------------
    def create_provider_set_from_per_realization_csv_file(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleSummaryProviderSet:

        LOGGER.info(
            f"create_provider_set_from_per_realization_csv_file() starting - {csv_file_rel_path}"
        )
        timer = PerfTimer()

        created_providers: Dict[str, EnsembleSummaryProvider] = {}
        missing_storage_keys: Dict[str, str] = {}

        # Try and create/load providers from backing store
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5((ens_path + csv_file_rel_path).encode()).hexdigest()
            storage_key = f"ens_csv__{hashval}"
            provider = self._create_provider_instance_from_backing_store(storage_key)
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(
                    f"Loaded summary provider for {ens_name} from backing store"
                )
            else:
                missing_storage_keys[ens_name] = storage_key

        # If there are remaining keys AND we're allowed to write to storage, we'll load
        # the CSV/SMRY data, write data to storage and then try and load again
        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, storage_key in dict(missing_storage_keys).items():
                LOGGER.info(
                    f"Importing/saving CSV summary data for ensemble: {ens_name}"
                )
                timer.lap_s()

                ens_path = ensembles[ens_name]
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                et_create_scratch_ens_s = timer.lap_s()

                ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
                et_load_csv_s = timer.lap_s()

                self._write_data_to_backing_store(storage_key, ensemble_df)
                et_write_s = timer.lap_s()

                provider = self._create_provider_instance_from_backing_store(
                    storage_key
                )
                if provider:
                    created_providers[ens_name] = provider
                    del missing_storage_keys[ens_name]
                    LOGGER.info(
                        f"Saved summary provider for {ens_name} to backing store ("
                        f"create_scratch_ens={et_create_scratch_ens_s:.2f}s, "
                        f"load_csv={et_load_csv_s:.2f}s, "
                        f"write={et_write_s:.2f}s)"
                    )

        if missing_storage_keys:
            raise ValueError(
                f"Failed to load/create provider(s) for {len(missing_storage_keys)} ensembles"
            )

        LOGGER.info(
            f"create_provider_set_from_per_realization_csv_file() finished "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleSummaryProviderSet(created_providers)

    # -------------------------------------------------------------------------
    def create_provider_set_from_ensemble_smry(
        self, ensembles: Dict[str, str], time_index: str
    ) -> EnsembleSummaryProviderSet:

        LOGGER.info("create_provider_set_from_ensemble_smry() starting...")
        timer = PerfTimer()

        created_providers: Dict[str, EnsembleSummaryProvider] = {}
        missing_storage_keys: Dict[str, str] = {}

        # Try and create/load from backing store
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5(ens_path.encode()).hexdigest()
            ens_storage_key = f"ens_smry__{hashval}__{time_index}"

            provider = self._create_provider_instance_from_backing_store(
                ens_storage_key
            )
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(
                    f"Loaded summary provider for {ens_name} from backing store"
                )
            else:
                missing_storage_keys[ens_name] = ens_storage_key

        # If there are remaining keys to create, we'll load the smry data using
        # FMU, write the data to storage and then try and load again
        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, ens_storage_key in dict(missing_storage_keys).items():
                LOGGER.info(f"Importing/saving summary data for ensemble: {ens_name}")
                timer.lap_s()

                ens_path = ensembles[ens_name]

                # Experiment with importing smry data per realization instead of whole
                # dataframe for entire ensemble (pyarrow only)
                if (
                    self._backing_type
                    is BackingType.ARROW_PER_REAL_SMRY_IMPORT_EXPERIMENTAL
                ):
                    per_real_dfs = _load_smry_dataframe_per_realization(
                        ens_path, time_index
                    )
                    et_import_smry_s = timer.lap_s()

                    EnsembleSummaryProviderImplArrow.write_backing_store_from_per_realization_dataframes_experimental(
                        self._storage_dir, ens_storage_key, per_real_dfs
                    )
                    et_write_s = timer.lap_s()
                else:
                    ensemble_df = _load_smry_single_dataframe_for_ensemble(
                        ens_path, time_index
                    )
                    et_import_smry_s = timer.lap_s()

                    self._write_data_to_backing_store(ens_storage_key, ensemble_df)
                    et_write_s = timer.lap_s()

                provider = self._create_provider_instance_from_backing_store(
                    ens_storage_key
                )
                if provider:
                    created_providers[ens_name] = provider
                    del missing_storage_keys[ens_name]
                    LOGGER.info(
                        f"Saved summary provider for {ens_name} to backing store ("
                        f"import_smry={et_import_smry_s:.2f}s, write={et_write_s:.2f}s)"
                    )

        # Should not be any keys missing
        if missing_storage_keys:
            raise ValueError(
                f"Failed to load/create provider(s) for {len(missing_storage_keys)} ensembles"
            )

        LOGGER.info(
            f"create_provider_set_from_ensemble_smry() finished "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleSummaryProviderSet(created_providers)

    # -------------------------------------------------------------------------
    # Simple solution for creating EnsembleSummaryProvider instances from backing store
    # based on the configured backing type.
    def _create_provider_instance_from_backing_store(
        self, storage_key: str
    ) -> Optional[EnsembleSummaryProvider]:
        if (
            self._backing_type is BackingType.ARROW
            or self._backing_type is BackingType.ARROW_PER_REAL_SMRY_IMPORT_EXPERIMENTAL
        ):
            return EnsembleSummaryProviderImplArrow.from_backing_store(
                self._storage_dir, storage_key
            )

        if self._backing_type is BackingType.PARQUET:
            return EnsembleSummaryProviderImplParquet.from_backing_store(
                self._storage_dir, storage_key
            )

        if self._backing_type is BackingType.INMEM_PARQUET:
            return EnsembleSummaryProviderImplInMemParquet.from_backing_store(
                self._storage_dir, storage_key
            )

        raise NotImplementedError("Unhandled backing type")

    # -------------------------------------------------------------------------
    # Simple solution for writing data to backing store according to the backing
    # type that is configured for the factory
    def _write_data_to_backing_store(
        self, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:
        if (
            self._backing_type is BackingType.ARROW
            or self._backing_type is BackingType.ARROW_PER_REAL_SMRY_IMPORT_EXPERIMENTAL
        ):
            EnsembleSummaryProviderImplArrow.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )

        elif self._backing_type is BackingType.PARQUET:
            EnsembleSummaryProviderImplParquet.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )

        elif self._backing_type is BackingType.INMEM_PARQUET:
            EnsembleSummaryProviderImplInMemParquet.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )

        else:
            raise NotImplementedError("Unhandled backing type")


# -------------------------------------------------------------------------
# @profile
def _load_smry_single_dataframe_for_ensemble(
    ens_path: str, time_index: str
) -> pd.DataFrame:

    LOGGER.debug(f"_load_smry_single_dataframe_for_ensemble() starting - {ens_path}")
    timer = PerfTimer()

    scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
    et_create_scratch_ens_s = timer.lap_s()

    ensemble_df = scratch_ensemble.load_smry(time_index=time_index)
    et_load_smry_s = timer.lap_s()

    LOGGER.debug(
        f"_load_smry_single_dataframe_for_ensemble() "
        f"finished in: {timer.elapsed_s():.2f}s ("
        f"create_scratch_ens={et_create_scratch_ens_s:.2f}s "
        f"load_smry={et_load_smry_s:.2f}s)"
    )

    return ensemble_df


# -------------------------------------------------------------------------
# @profile
def _load_smry_dataframe_per_realization(
    ens_path: str, time_index: str
) -> List[pd.DataFrame]:

    LOGGER.debug(f"_load_smry_dataframe_per_realization() starting - {ens_path}")
    timer = PerfTimer()

    scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
    et_create_scratch_ens_s = timer.lap_s()

    real_df_list = []
    for _realidx, realization in scratch_ensemble.realizations.items():
        # Note that default caching (cache_eclsum=True) seems faster even if we're
        # at realization level, but uses more memory
        real_df = realization.load_smry(time_index=time_index)
        real_df_list.append(real_df)
    et_aggr_load_smry_s = timer.lap_s()

    LOGGER.debug(
        f"_load_smry_dataframe_per_realization() "
        f"finished in: {timer.elapsed_s():.2f}s ("
        f"create_scratch_ens={et_create_scratch_ens_s:.2f}s "
        f"aggr_load_smry={et_aggr_load_smry_s:.2f}s)"
    )

    return real_df_list
