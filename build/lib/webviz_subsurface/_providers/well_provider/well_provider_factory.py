import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from webviz_config.webviz_factory import WebvizFactory
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WebvizRunMode

from webviz_subsurface._utils.perf_timer import PerfTimer

from ._provider_impl_file import ProviderImplFile
from .well_provider import WellProvider

LOGGER = logging.getLogger(__name__)


class WellProviderFactory(WebvizFactory):
    def __init__(self, root_storage_folder: Path, allow_storage_writes: bool) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._allow_storage_writes = allow_storage_writes

        LOGGER.info(f"WellProviderFactory init: storage_dir={self._storage_dir}")

        if self._allow_storage_writes:
            os.makedirs(self._storage_dir, exist_ok=True)

    @staticmethod
    def instance() -> "WellProviderFactory":
        """Static method to access the singleton instance of the factory."""

        factory = WEBVIZ_FACTORY_REGISTRY.get_factory(WellProviderFactory)
        if not factory:
            app_instance_info = WEBVIZ_FACTORY_REGISTRY.app_instance_info
            storage_folder = app_instance_info.storage_folder
            allow_writes = app_instance_info.run_mode != WebvizRunMode.PORTABLE

            factory = WellProviderFactory(storage_folder, allow_writes)

            # Store the factory object in the global factory registry
            WEBVIZ_FACTORY_REGISTRY.set_factory(WellProviderFactory, factory)

        return factory

    def create_from_well_files(
        self, well_folder: str, well_suffix: str, md_logname: Optional[str]
    ) -> WellProvider:
        timer = PerfTimer()

        file_pattern = str(Path(well_folder) / f"*{well_suffix}")
        storage_key = f"from_files__{_make_hash_string(f'{file_pattern}_{md_logname}')}"

        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if provider:
            LOGGER.info(
                f"Loaded well provider from backing store in {timer.elapsed_s():.2f}s ("
                f"file_pattern={file_pattern})"
            )
            return provider

        # We can only import data from data source if storage writes are allowed
        if not self._allow_storage_writes:
            raise ValueError(f"Failed to load well provider for {file_pattern}")

        LOGGER.info(f"Importing/writing well data for: {file_pattern}")

        timer.lap_s()
        src_file_names = sorted(
            [str(filename) for filename in Path(well_folder).glob(f"*{well_suffix}")]
        )
        et_discover_s = timer.lap_s()

        ProviderImplFile.write_backing_store(
            self._storage_dir,
            storage_key,
            well_file_names=src_file_names,
            md_logname=md_logname,
        )
        et_write_s = timer.lap_s()

        provider = ProviderImplFile.from_backing_store(self._storage_dir, storage_key)
        if not provider:
            raise ValueError(f"Failed to load/create well provider for {file_pattern}")

        LOGGER.info(
            f"Saved well provider to backing store in {timer.elapsed_s():.2f}s ("
            f"discover={et_discover_s:.2f}s, write={et_write_s:.2f}s, file_pattern={file_pattern})"
        )

        return provider


def _make_hash_string(string_to_hash: str) -> str:
    # There is no security risk here and chances of collision should be very slim
    return hashlib.md5(string_to_hash.encode()).hexdigest()  # nosec
