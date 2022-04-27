import hashlib
import logging
import os
from pathlib import Path
from typing import List

from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._provider_impl_file import ProviderImplFile
from ._surface_discovery import (
    discover_observed_surface_files,
    discover_per_realization_surface_files,
)
from .ensemble_surface_provider import EnsembleSurfaceProvider

LOGGER = logging.getLogger(__name__)


class EnsembleSurfaceProviderFactory(WebvizFactory):
    def __init__(
        self,
        root_storage_folder: Path,
        allow_storage_writes: bool,
        avoid_copying_surfaces: bool,
    ) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes
        self._avoid_copying_surfaces = avoid_copying_surfaces

        LOGGER.info(
            f"EnsembleSurfaceProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsembleSurfaceProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsembleSurfaceProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE
            dont_copy_surfs = app_instance_info.run_mode == WebvizRunMode.NON_PORTABLE

            factory = EnsembleSurfaceProviderFactory(
                root_storage_folder=storage_folder,
                allow_storage_writes=allow_writes,
                avoid_copying_surfaces=dont_copy_surfs,
            )

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsembleSurfaceProviderFactory, factory)

        return factory

    def create_from_ensemble_surface_files(
        self,
        ens_path: str,
        rel_surface_folder: str = "share/results/maps",
        attribute_filter: List[str] = None,
    ) -> EnsembleSurfaceProvider:
        timer = PerfTimer()
        string_to_hash = (
            f"{ens_path}_{rel_surface_folder}"
            if attribute_filter is None
            else (
                f"{ens_path}_{rel_surface_folder}_"
                f"{'_'.join([str(attr) for attr in attribute_filter])}"
            )
        )
        storage_key = f"ens__{_make_hash_string(string_to_hash)}"
        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if provider:
            LOGGER.info(
                f"Loaded surface provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load surface provider for {ens_path}")

        LOGGER.info(f"Importing/copying surface data for: {ens_path}")

        timer.lap_s()
        sim_surface_files = discover_per_realization_surface_files(
            ens_path, rel_surface_folder, attribute_filter
        )
        obs_surface_files = discover_observed_surface_files(ens_path, attribute_filter)
        et_discover_s = timer.lap_s()

        # As an optimization, avoid copying the surfaces into the backing store,
        # typically when  we're running in non-portable mode
        ProviderImplFile.write_backing_store(
            self._storage_dir,
            storage_key,
            sim_surfaces=sim_surface_files,
            obs_surfaces=obs_surface_files,
            avoid_copying_surfaces=self._avoid_copying_surfaces,
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if not provider:
            raise ValueError(f"Failed to load/create surface provider for {ens_path}")

        LOGGER.info(
            f"Saved surface provider to backing store in {timer.elapsed_s():.2f}s ("
            f"discover={et_discover_s:.2f}s, write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
