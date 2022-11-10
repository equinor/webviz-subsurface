import hashlib
import logging
import os
from pathlib import Path
from typing import List

from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._egrid_file_discovery import discover_per_realization_eclipse_files
from ._roff_file_discovery import discover_per_realization_roff_files
from .ensemble_grid_provider import EnsembleGridProvider
from .provider_impl_egrid import ProviderImplEgrid
from .provider_impl_roff import ProviderImplRoff

LOGGER = logging.getLogger(__name__)


class EnsembleGridProviderFactory(WebvizFactory):
    def __init__(
        self,
        root_storage_folder: Path,
        allow_storage_writes: bool,
        avoid_copying_grid_data: bool,
    ) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes
        self._avoid_copying_grid_data = avoid_copying_grid_data

        LOGGER.info(
            f"EnsembleGridProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsembleGridProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleGridProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE
            dont_copy_grid_data = (
                app_instance_info.run_mode == WebvizRunMode.NON_PORTABLE
            )

            factory = EnsembleGridProviderFactory(
                root_storage_folder=storage_folder,
                allow_storage_writes=allow_writes,
                avoid_copying_grid_data=dont_copy_grid_data,
            )

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleGridProviderFactory, factory)

        return factory

    def create_from_roff_files(
        self, ens_path: str, grid_name: str, attribute_filter: List[str] = None
    ) -> EnsembleGridProvider:
        timer = PerfTimer()
        string_to_hash = (
            f"{ens_path}_{grid_name}"
            if attribute_filter is None
            else f"{ens_path}_{grid_name}_{'_'.join([str(attr) for attr in attribute_filter])}"
        )
        storage_key = f"ens__{_make_hash_string(string_to_hash)}"
        provider = ProviderImplRoff.from_backing_store(self._storage_dir, storage_key)
        if provider:
            LOGGER.info(
                f"Loaded grid provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load grid provider for {ens_path}")

        LOGGER.info(f"Importing/copying grid data for: {ens_path}")

        timer.lap_s()
        grid_info, grid_parameters_info = discover_per_realization_roff_files(
            ens_path, grid_name, attribute_filter
        )

        # As an optimization, avoid copying the grid data into the backing store,
        # typically when  we're running in non-portable mode
        ProviderImplRoff.write_backing_store(
            self._storage_dir,
            storage_key,
            grid_geometries_info=grid_info,
            grid_parameters_info=grid_parameters_info,
            avoid_copying_grid_data=self._avoid_copying_grid_data,
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplRoff.from_backing_store(self._storage_dir, storage_key)
        if not provider:
            raise ValueError(f"Failed to load/create grid provider for {ens_path}")

        LOGGER.info(
            f"Saved grid provider to backing store in {timer.elapsed_s():.2f}s ("
            f" write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider

    def create_from_eclipse_files(
        self,
        ens_path: str,
        grid_name: str,
        init_properties: List[str],
        restart_properties: List[str],
    ) -> EnsembleGridProvider:
        timer = PerfTimer()

        string_to_hash = f"{ens_path}_{grid_name}_egrid"
        storage_key = f"ens__{_make_hash_string(string_to_hash)}"
        provider = ProviderImplEgrid.from_backing_store(
            self._storage_dir, storage_key, init_properties, restart_properties
        )
        if provider:
            LOGGER.info(
                f"Loaded grid provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load grid provider for {ens_path}")

        LOGGER.info(f"Importing/copying grid data for: {ens_path}")

        timer.lap_s()
        eclipse_case_paths = discover_per_realization_eclipse_files(ens_path, grid_name)

        # As an optimization, avoid copying the grid data into the backing store,
        # typically when  we're running in non-portable mode
        ProviderImplEgrid.write_backing_store(
            self._storage_dir,
            storage_key,
            eclipse_case_paths=eclipse_case_paths,
            avoid_copying_grid_data=self._avoid_copying_grid_data,
        )
        et_write_s = timer.lap_s()
        provider = ProviderImplEgrid.from_backing_store(
            self._storage_dir, storage_key, init_properties, restart_properties
        )
        if not provider:
            raise ValueError(f"Failed to load/create grid provider for {ens_path}")

        LOGGER.info(
            f"Saved grid provider to backing store in {timer.elapsed_s():.2f}s ("
            f" write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
