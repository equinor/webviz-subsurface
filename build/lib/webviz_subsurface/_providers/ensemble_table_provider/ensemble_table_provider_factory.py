import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict

import pandas as pd
from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

# The fmu.ensemble dependency ecl is only available for Linux,
# hence, ignore any import exception here to make
# it still possible to use the PvtPlugin on
# machines with other OSes.
#
# NOTE: Functions in this file cannot be used
#       on non-Linux OSes.
try:
    from fmu.ensemble import ScratchEnsemble
except ImportError:
    pass

from webviz_subsurface._utils.perf_timer import PerfTimer

from ..ensemble_summary_provider._arrow_unsmry_import import (
    load_per_realization_arrow_unsmry_files,
)
from ..ensemble_summary_provider._csv_import import load_per_real_csv_file_using_fmu
from .ensemble_table_provider import EnsembleTableProvider
from .ensemble_table_provider_impl_arrow import EnsembleTableProviderImplArrow

LOGGER = logging.getLogger(__name__)


class EnsembleTableProviderFactory(WebvizFactory):
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        LOGGER.info(
            f"EnsembleTableProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsembleTableProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleTableProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            factory = EnsembleTableProviderFactory(storage_folder, allow_writes)

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleTableProviderFactory, factory)

        return factory

    def create_from_ensemble_csv_file(
        self,
        csv_file: Path,
    ) -> EnsembleTableProvider:
        """Create EnsembleTableProvider from aggregated CSV file.
        The CSV file is assumed to contain data for a single ensemble and must contain
        a REAL column.
        If the CSV file contains an `ENSEMBLE` column it will be ignored, but an exception
        will be thrown if it is present and it contains multiple ensemble names.
        """

        timer = PerfTimer()

        storage_key = f"ens_csv__{_make_hash_string(str(csv_file))}"

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )
        if provider:
            LOGGER.info(
                f"Loaded table provider (CSV) from backing store in "
                f"{timer.elapsed_s():.2f}s (csv_file={csv_file})"
            )
            return provider

        # We can only import data from csv if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load table provider (CSV) for {csv_file}")

        LOGGER.info(f"Importing/saving CSV data for: {csv_file}")

        timer.lap_s()
        ensemble_df = pd.read_csv(csv_file)

        if "ENSEMBLE" in ensemble_df.columns:
            if ensemble_df["ENSEMBLE"].nunique() > 1:
                raise KeyError("Input data contains more than one unique ensemble name")

        et_import_csv_s = timer.lap_s()

        if ensemble_df.empty:
            raise ValueError("Import resulted in empty DataFrame")
        if "REAL" not in ensemble_df.columns:
            raise ValueError("No REAL column present in input data")

        EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
            self._storage_dir, storage_key, ensemble_df
        )
        et_write_s = timer.lap_s()

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/create provider for {csv_file}")

        LOGGER.info(
            f"Saved table provider (CSV) to backing store in {timer.elapsed_s():.2f}s ("
            f"import_csv={et_import_csv_s:.2f}s, "
            f"write={et_write_s:.2f}s, "
            f"csv_file={csv_file})"
        )

        return provider

    def create_from_per_realization_csv_file(
        self, ens_path: str, csv_file_rel_path: str
    ) -> EnsembleTableProvider:
        """Create EnsembleTableProvider from per realization CSV files.

        Note that the returned table provider will not be able to return vector
        metadata.
        """

        timer = PerfTimer()

        storage_key = f"per_real_csv__{_make_hash_string(ens_path + csv_file_rel_path)}"
        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )

        if provider:
            LOGGER.info(
                f"Loaded table provider (per real CSV) from backing store in "
                f"{timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path}, csv_file_rel_path={csv_file_rel_path})"
            )
            return provider

        # We can only import data from CSV if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(
                f"Failed to load table provider (per real CSV) for {ens_path}"
            )

        LOGGER.info(f"Importing/saving per real CSV data for: {ens_path}")

        timer.lap_s()

        ensemble_df = load_per_real_csv_file_using_fmu(ens_path, csv_file_rel_path)
        et_import_csv_s = timer.lap_s()

        EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
            self._storage_dir, storage_key, ensemble_df
        )
        et_write_s = timer.lap_s()

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )

        if not provider:
            raise ValueError(
                f"Failed to load/create provider (per real CSV) for {ens_path}"
            )

        LOGGER.info(
            f"Saved table provider (per real CSV) to backing store in {timer.elapsed_s():.2f}s ("
            f"import_csv={et_import_csv_s:.2f}s, write={et_write_s:.2f}s, "
            f"ens_path={ens_path}, csv_file_rel_path={csv_file_rel_path})"
        )

        return provider

    def create_from_per_realization_arrow_file(
        self, ens_path: str, rel_file_pattern: str
    ) -> EnsembleTableProvider:
        """Create EnsembleTableProvider from per realization data in .arrow format.

        The `rel_file_pattern` parameter must specify a relative (per realization) file pattern
        that will be used to find the wanted .arrow files within each realization. The file
        pattern is realtive to each realizations's `runpath`.
        """

        timer = PerfTimer()

        storage_key = (
            f"per_real_arrow__{_make_hash_string(ens_path + rel_file_pattern)}"
        )
        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )
        if provider:
            LOGGER.info(
                f"Loaded table provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load table provider for {ens_path}")

        LOGGER.info(f"Importing/saving arrow table data for: {ens_path}")

        timer.lap_s()
        per_real_tables = load_per_realization_arrow_unsmry_files(
            ens_path, rel_file_pattern
        )
        if not per_real_tables:
            raise ValueError(f"Could not find any .arrow files for ens_path={ens_path}")
        et_import_smry_s = timer.lap_s()

        try:
            EnsembleTableProviderImplArrow.write_backing_store_from_per_realization_tables(
                self._storage_dir, storage_key, per_real_tables
            )
        except ValueError as exc:
            raise ValueError(f"Failed to write backing store for: {ens_path}") from exc

        et_write_s = timer.lap_s()

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/create table provider for {ens_path}")

        LOGGER.info(
            f"Saved table provider to backing store in {timer.elapsed_s():.2f}s ("
            f"import_smry={et_import_smry_s:.2f}s, write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider

    def create_from_per_realization_parameter_file(
        self, ens_path: str
    ) -> EnsembleTableProvider:
        """Create EnsembleTableProvider from parameter files.

        Note that the returned table provider will not be able to return metadata.
        """

        LOGGER.info("create_provider_from_per_realization_parameter_file() ...")

        timer = PerfTimer()

        storage_key = f"parameters_{_make_hash_string(ens_path + '_parameters')}"

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )

        if provider:
            LOGGER.info(
                f"Loaded table provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load table provider for {ens_path}")

        LOGGER.info(f"Importing parameters for: {ens_path}")

        timer.lap_s()

        scratch_ensemble = ScratchEnsemble("ens_name_tmp", ens_path).filter("OK")
        ensemble_df = scratch_ensemble.parameters
        del scratch_ensemble
        elapsed_load_parameters_s = timer.lap_s()

        try:
            EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )
        except ValueError as exc:
            raise ValueError(f"Failed to write backing store for: {ens_path}") from exc

        et_write_s = timer.lap_s()

        provider = EnsembleTableProviderImplArrow.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/crate table provider for {ens_path}")

        LOGGER.info(
            f"Saved table provider to backing store in {timer.elapsed_s():.2f}s ("
            f"load_parameters={elapsed_load_parameters_s:.2f}s, "
            f"write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider

    def create_provider_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> Dict[str, EnsembleTableProvider]:
        """Creates a dictionary of table providers from an aggregated CSV file with
        ENSEMBLE column. The CSV file can have multiple ensembles in the ENSEMBLE column.
        (This is not accepted by the create_from_ensemble_csv_file function)

        Aggregated csv-files per ensemble is the preferred method.
        """
        LOGGER.info(f"create_provider_set_from_aggregated_csv_file() - {aggr_csv_file}")

        hashval = _make_hash_string(str(aggr_csv_file))
        main_storage_key = f"aggr_csv__{hashval}"

        storage_keys_to_load: Dict[str, str] = {}
        json_fn = self._storage_dir / (f"{main_storage_key}.json")
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
                storage_key = f"{main_storage_key}__{ens_name}"
                ensemble_df = aggregated_df[aggregated_df["ENSEMBLE"] == ens_name]
                EnsembleTableProviderImplArrow.write_backing_store_from_ensemble_dataframe(
                    self._storage_dir, storage_key, ensemble_df
                )
                storage_keys_to_load[ens_name] = storage_key

            with open(json_fn, "w") as file:
                json.dump(storage_keys_to_load, file)

        created_providers: Dict[str, EnsembleTableProvider] = {}
        for ens_name, storage_key in storage_keys_to_load.items():
            provider = EnsembleTableProviderImplArrow.from_backing_store(
                self._storage_dir, storage_key
            )
            if provider:
                created_providers[ens_name] = provider

        num_missing_models = len(storage_keys_to_load) - len(created_providers)
        if num_missing_models > 0:
            raise ValueError(f"Failed to load data for {num_missing_models} ensembles")

        LOGGER.info(f"Loaded {len(created_providers)} providers from backing store")

        return created_providers


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
