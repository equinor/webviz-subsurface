import hashlib
import logging
import os
from pathlib import Path

from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._polygon_discovery import discover_per_realization_polygons_files
from ._provider_impl_file import ProviderImplFile
from .ensemble_polygon_provider import EnsemblePolygonProvider

LOGGER = logging.getLogger(__name__)


class EnsemblePolygonProviderFactory(WebvizFactory):
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        LOGGER.info(
            f"EnsemblePolygonProviderFactory init: storage_dir={self._storage_dir}"
        )

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "EnsemblePolygonProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(EnsemblePolygonProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            factory = EnsemblePolygonProviderFactory(storage_folder, allow_writes)

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(EnsemblePolygonProviderFactory, factory)

        return factory

    def create_from_ensemble_polygon_files(
        self,
        ens_path: str,
        polygon_path_pattern: str,
    ) -> EnsemblePolygonProvider:
        timer = PerfTimer()

        storage_key = f"ens__{_make_hash_string(ens_path)}"
        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if provider:
            LOGGER.info(
                f"Loaded polygon provider from backing store in {timer.elapsed_s():.2f}s ("
                f"ens_path={ens_path})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load polygon provider for {ens_path}")

        LOGGER.info(f"Importing/copying polygon data for: {ens_path}")

        timer.lap_s()
        sim_polygons_files = discover_per_realization_polygons_files(
            ens_path,
            polygon_path_pattern,
        )

        et_discover_s = timer.lap_s()

        ProviderImplFile.write_backing_store(
            self._storage_dir,
            storage_key,
            sim_polygons=sim_polygons_files,
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if not provider:
            raise ValueError(f"Failed to load/create polygon provider for {ens_path}")

        LOGGER.info(
            f"Saved polygon provider to backing store in {timer.elapsed_s():.2f}s ("
            f"discover={et_discover_s:.2f}s, write={et_write_s:.2f}s, ens_path={ens_path})"
        )

        return provider


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
