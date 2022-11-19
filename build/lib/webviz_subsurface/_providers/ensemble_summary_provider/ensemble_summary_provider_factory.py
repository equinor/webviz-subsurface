import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._arrow_unsmry_import import load_per_realization_arrow_unsmry_files
from ._csv_import import (
    load_ensemble_summary_csv_file,
    load_per_real_csv_file_using_fmu,
)
from ._provider_impl_arrow_lazy import ProviderImplArrowLazy
from ._provider_impl_arrow_presampled import ProviderImplArrowPresampled
from ._resampling import Frequency, resample_single_real_table
from .ensemble_summary_provider import EnsembleSummaryProvider

LOGGER = logging.getLogger(__name__)


class EnsembleSummaryProviderFactory(WebvizFactory):
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        LOGGER.info(
            f"EnsembleSummaryProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsembleSummaryProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleSummaryProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            factory = EnsembleSummaryProviderFactory(storage_folder, allow_writes)

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleSummaryProviderFactory, factory)

        return factory

    def create_from_ensemble_csv_file(
        self,
        csv_file: Path,
        ensemble_filter: Optional[str] = None,
    ) -> EnsembleSummaryProvider:
        """Create EnsembleSummaryProvider from aggregated CSV file.
        The CSV file is assumed to contain data for a single ensemble and must contain
        columns for `REAL` and `DATE` in addition to the actual numeric vectors.
        If the CSV file contains an `ENSEMBLE` column it will be ignored, but an exception
        will be thrown if it is present and it contains multiple ensemble names.

        Note that the returned summary provider does not support resampling, nor will it
        be able to return vector metadata.
        """

        timer = PerfTimer()

        storage_key = "ens_csv"
        if ensemble_filter is not None:
            storage_key += f"_filtered_on_{ensemble_filter}"
        storage_key += f"__{_make_hash_string(str(csv_file))}"

        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )
        if provider:
            LOGGER.info(
                f"Loaded summary provider (CSV) from backing store in "
                f"{timer.elapsed_s():.2f}s (csv_file={csv_file})"
            )
            return provider

        # We can only import data from CSV if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load summary provider (CSV) for {csv_file}")

        LOGGER.info(f"Importing/saving CSV summary data for: {csv_file}")

        timer.lap_s()
        ensemble_df = load_ensemble_summary_csv_file(csv_file, ensemble_filter)
        et_import_csv_s = timer.lap_s()

        if len(ensemble_df) == 0:
            raise ValueError("Import resulted in empty DataFrame")
        if "DATE" not in ensemble_df.columns:
            raise ValueError("No DATE column present in input data")
        if "REAL" not in ensemble_df.columns:
            raise ValueError("No REAL column present in input data")

        ProviderImplArrowPresampled.write_backing_store_from_ensemble_dataframe(
            self._storage_dir, storage_key, ensemble_df
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/create provider for {csv_file}")

        LOGGER.info(
            f"Saved summary provider (CSV) to backing store in {timer.elapsed_s():.2f}s ("
            f"import_csv={et_import_csv_s:.2f}s, "
            f"write={et_write_s:.2f}s, "
            f"csv_file={csv_file})"
        )

        return provider

    def create_from_per_realization_csv_file(
        self, ens_path: str, csv_file_rel_path: str
    ) -> EnsembleSummaryProvider:
        """Create EnsembleSummaryProvider from per realization CSV files.

        Note that the returned summary provider does not support resampling, nor will it
        be able to return vector metadata.
        """

        timer = PerfTimer()

        storage_key = f"per_real_csv__{_make_hash_string(ens_path + csv_file_rel_path)}"
        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )

        if provider:
            LOGGER.info(
                f"Loaded summary provider (per real CSV) from backing store in "
                f"{timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path}, csv_file_rel_path={csv_file_rel_path})"
            )
            return provider

        # We can only import data from CSV if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(
                f"Failed to load summary provider (per real CSV) for {ens_path}"
            )

        LOGGER.info(f"Importing/saving per real CSV summary data for: {ens_path}")

        timer.lap_s()

        ensemble_df = load_per_real_csv_file_using_fmu(ens_path, csv_file_rel_path)
        et_import_csv_s = timer.lap_s()

        ProviderImplArrowPresampled.write_backing_store_from_ensemble_dataframe(
            self._storage_dir, storage_key, ensemble_df
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )

        if not provider:
            raise ValueError(
                f"Failed to load/create provider (per real CSV) for {ens_path}"
            )

        LOGGER.info(
            f"Saved summary provider (per real CSV) to backing store in {timer.elapsed_s():.2f}s ("
            f"import_csv={et_import_csv_s:.2f}s, write={et_write_s:.2f}s, "
            f"ens_path={ens_path}, csv_file_rel_path={csv_file_rel_path})"
        )

        return provider

    def create_from_arrow_unsmry_lazy(
        self, ens_path: str, rel_file_pattern: str
    ) -> EnsembleSummaryProvider:
        """Create EnsembleSummaryProvider from per-realization unsmry data in .arrow format.

        The `rel_file_pattern` parameter must specify a relative (per realization) file pattern
        that will be used to find the wanted .arrow files within each realization. The file
        pattern is relative to each realization's `runpath`.
        Typically the file pattern will be: "share/results/unsmry/*.arrow"

        The returned summary provider supports lazy resampling.
        """

        timer = PerfTimer()

        storage_key = (
            f"arrow_unsmry_lazy__{_make_hash_string(ens_path + rel_file_pattern)}"
        )
        provider = ProviderImplArrowLazy.from_backing_store(
            self._storage_dir, storage_key
        )
        if provider:
            LOGGER.info(
                f"Loaded lazy summary provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load lazy summary provider for {ens_path}")

        LOGGER.info(f"Importing/saving arrow summary data for: {ens_path}")

        timer.lap_s()
        per_real_tables = load_per_realization_arrow_unsmry_files(
            ens_path, rel_file_pattern
        )
        if not per_real_tables:
            raise ValueError(
                f"Could not find any .arrow unsmry files for ens_path={ens_path}"
            )
        et_import_smry_s = timer.lap_s()

        try:
            ProviderImplArrowLazy.write_backing_store_from_per_realization_tables(
                self._storage_dir, storage_key, per_real_tables
            )
        except ValueError as exc:
            raise ValueError(f"Failed to write backing store for: {ens_path}") from exc

        et_write_s = timer.lap_s()

        provider = ProviderImplArrowLazy.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/create lazy provider for {ens_path}")

        LOGGER.info(
            f"Saved lazy summary provider to backing store in {timer.elapsed_s():.2f}s ("
            f"import_smry={et_import_smry_s:.2f}s, write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider

    def create_from_arrow_unsmry_presampled(
        self,
        ens_path: str,
        rel_file_pattern: str,
        sampling_frequency: Optional[Frequency],
    ) -> EnsembleSummaryProvider:
        """Create EnsembleSummaryProvider from per-realization unsmry data in .arrow format.

        The `rel_file_pattern` parameter must specify a relative (per realization) file pattern
        that will be used to find the wanted .arrow files within each realization. The file
        pattern is relative to each realization's `runpath`.
        Typically the file pattern will be: "share/results/unsmry/*.arrow"

        This factory method will sample the input data according to the specified
        `sampling_frequency` during import.

        The returned summary provider does not support lazy resampling, but will always
        return data with the above specified frequency .
        """

        timer = PerfTimer()

        freq_str = sampling_frequency.value if sampling_frequency else "raw"
        hash_str = _make_hash_string(ens_path + rel_file_pattern)
        storage_key = f"arrow_unsmry_presampled_{freq_str}__{hash_str}"
        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )
        if provider:
            LOGGER.info(
                f"Loaded presampled summary provider from backing store in "
                f"{timer.elapsed_s():.2f}s ("
                f"sampling_frequency={sampling_frequency}, ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(
                f"Failed to load presampled summary provider for {ens_path}"
            )

        LOGGER.info(f"Importing/saving arrow summary data for: {ens_path}")

        timer.lap_s()
        per_real_tables = load_per_realization_arrow_unsmry_files(
            ens_path, rel_file_pattern
        )
        if not per_real_tables:
            raise ValueError(
                f"Could not find any .arrow unsmry files for ens_path={ens_path}"
            )
        et_import_smry_s = timer.lap_s()

        if sampling_frequency is not None:
            for real_num, table in per_real_tables.items():
                per_real_tables[real_num] = resample_single_real_table(
                    table, sampling_frequency
                )
        et_resample_s = timer.lap_s()

        ProviderImplArrowPresampled.write_backing_store_from_per_realization_tables(
            self._storage_dir, storage_key, per_real_tables
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplArrowPresampled.from_backing_store(
            self._storage_dir, storage_key
        )
        if not provider:
            raise ValueError(f"Failed to load/create provider for {ens_path}")

        LOGGER.info(
            f"Saved presampled summary provider to backing store in {timer.elapsed_s():.2f}s ("
            f"import_smry={et_import_smry_s:.2f}s, "
            f"resample={et_resample_s:.2f}s, "
            f"write={et_write_s:.2f}s, "
            f"ens_path={ens_path})"
        )

        return provider


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
