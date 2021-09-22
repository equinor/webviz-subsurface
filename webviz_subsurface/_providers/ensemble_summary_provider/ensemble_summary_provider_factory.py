import sys
from pathlib import Path
import os
import hashlib
import logging

if sys.version_info >= (3, 8):
    from typing import Dict, Optional, Literal
else:
    from typing import Dict, Optional
    from typing_extensions import Literal

# pylint: disable=wrong-import-position
from fmu.ensemble import ScratchEnsemble

from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_factory import WebvizFactory

from webviz_subsurface._utils.perf_timer import PerfTimer
from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_set import EnsembleSummaryProviderSet
from ._provider_impl_arrow_lazy import EnsembleSummaryProviderImplLAZYArrow
from ._provider_impl_arrow_presampled import EnsembleSummaryProviderImplArrow
from ._arrow_unsmry_import import load_per_realization_arrow_unsmry_files
from ._resampling import (
    Frequency,
    resample_single_real_table,
)


LOGGER = logging.getLogger(__name__)


# =============================================================================
class EnsembleSummaryProviderFactory(WebvizFactory):

    # -------------------------------------------------------------------------
    def __init__(self, root_storage_folder: Path) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = True

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

            factory = EnsembleSummaryProviderFactory(storage_folder)

            # Store the factory object in the registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleSummaryProviderFactory, factory)

        return factory

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
            storage_key = f"ens_csv__{_make_hash_string(ens_path + csv_file_rel_path)}"
            provider = EnsembleSummaryProviderImplArrow.from_backing_store(
                self._storage_dir, storage_key
            )
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

                EnsembleSummaryProviderImplArrow.write_backing_store_from_ensemble_dataframe(
                    self._storage_dir, storage_key, ensemble_df
                )
                et_write_s = timer.lap_s()

                provider = EnsembleSummaryProviderImplArrow.from_backing_store(
                    self._storage_dir, storage_key
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
    def create_provider_set_from_arrow_unsmry_lazy(
        self,
        ensembles: Dict[str, str],
        report_frequency_str: Literal["daily", "weekly", "monthly", "yearly", "raw"],
    ) -> EnsembleSummaryProviderSet:

        LOGGER.info("create_provider_set_from_arrow_unsmry_lazy() starting...")
        timer = PerfTimer()

        frequency_enum: Optional[Frequency] = None
        if report_frequency_str != "raw":
            frequency_enum = Frequency(report_frequency_str)

        created_providers: Dict[str, EnsembleSummaryProvider] = {}
        missing_storage_keys: Dict[str, str] = {}

        for ens_name, ens_path in ensembles.items():
            ens_storage_key = f"ens_concat_ARR_LAZY__{_make_hash_string(ens_path)}"
            provider = EnsembleSummaryProviderImplLAZYArrow.from_backing_store(
                self._storage_dir, ens_storage_key, frequency_enum
            )
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(
                    f"Loaded summary provider for {ens_name} from backing store"
                )
            else:
                missing_storage_keys[ens_name] = ens_storage_key

        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, ens_storage_key in dict(missing_storage_keys).items():
                LOGGER.info(
                    f"Importing/saving arrow summary data for ensemble: {ens_name}"
                )
                timer.lap_s()

                ens_path = ensembles[ens_name]
                per_real_tables = load_per_realization_arrow_unsmry_files(ens_path)
                if not per_real_tables:
                    raise ValueError(
                        f"Could not find any .arrow unsmry files for ens_path={ens_path}"
                    )
                et_import_smry_s = timer.lap_s()

                EnsembleSummaryProviderImplLAZYArrow.write_backing_store_from_per_realization_tables(
                    self._storage_dir, ens_storage_key, per_real_tables
                )
                et_write_s = timer.lap_s()

                provider = EnsembleSummaryProviderImplLAZYArrow.from_backing_store(
                    self._storage_dir, ens_storage_key, frequency_enum
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
            f"create_provider_set_from_arrow_unsmry_lazy() finished "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleSummaryProviderSet(created_providers)

    # -------------------------------------------------------------------------
    def create_provider_set_from_arrow_unsmry_presampled(
        self,
        ensembles: Dict[str, str],
        sampling_frequency_str: Literal["daily", "weekly", "monthly", "yearly", "raw"],
    ) -> EnsembleSummaryProviderSet:

        LOGGER.info("create_provider_set_from_arrow_unsmry_presampled() starting...")
        timer = PerfTimer()

        frequency_enum: Optional[Frequency] = None
        if sampling_frequency_str != "raw":
            frequency_enum = Frequency(sampling_frequency_str)

        created_providers: Dict[str, EnsembleSummaryProvider] = {}
        missing_storage_keys: Dict[str, str] = {}

        for ens_name, ens_path in ensembles.items():
            ens_storage_key = f"ens_concat_PRESAMPLED_{sampling_frequency_str}__{_make_hash_string(ens_path)}"
            provider = EnsembleSummaryProviderImplArrow.from_backing_store(
                self._storage_dir, ens_storage_key
            )
            if provider:
                created_providers[ens_name] = provider
                LOGGER.info(
                    f"Loaded summary provider for {ens_name} from backing store"
                )
            else:
                missing_storage_keys[ens_name] = ens_storage_key

        if missing_storage_keys and self._allow_storage_writes:
            for ens_name, ens_storage_key in dict(missing_storage_keys).items():
                LOGGER.info(
                    f"Importing/saving arrow summary data for ensemble: {ens_name}"
                )
                timer.lap_s()

                ens_path = ensembles[ens_name]
                per_real_tables = load_per_realization_arrow_unsmry_files(ens_path)
                if not per_real_tables:
                    raise ValueError(
                        f"Could not find any .arrow unsmry files for ens_path={ens_path}"
                    )

                et_import_smry_s = timer.lap_s()

                if frequency_enum is not None:
                    for real_num, table in per_real_tables.items():
                        per_real_tables[real_num] = resample_single_real_table(
                            table, frequency_enum
                        )
                et_resample_s = timer.lap_s()

                EnsembleSummaryProviderImplArrow.write_backing_store_from_per_realization_tables(
                    self._storage_dir, ens_storage_key, per_real_tables
                )
                et_write_s = timer.lap_s()

                provider = EnsembleSummaryProviderImplArrow.from_backing_store(
                    self._storage_dir, ens_storage_key
                )

                if provider:
                    created_providers[ens_name] = provider
                    del missing_storage_keys[ens_name]
                    LOGGER.info(
                        f"Saved summary provider for {ens_name} to backing store ("
                        f"import_smry={et_import_smry_s:.2f}s, "
                        f"resample={et_resample_s:.2f}s, "
                        f"write={et_write_s:.2f}s)"
                    )

        # Should not be any keys missing
        if missing_storage_keys:
            raise ValueError(
                f"Failed to load/create provider(s) for {len(missing_storage_keys)} ensembles"
            )

        LOGGER.info(
            f"create_provider_set_from_arrow_unsmry_presampled() finished "
            f"- total time: {timer.elapsed_s():.2f}s"
        )

        return EnsembleSummaryProviderSet(created_providers)


# -------------------------------------------------------------------------
def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
