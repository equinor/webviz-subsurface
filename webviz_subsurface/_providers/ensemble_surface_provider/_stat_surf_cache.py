import datetime
import hashlib
import logging
import os
import pickle  # nosec
import uuid
from pathlib import Path
from typing import Optional

import xtgeo

from .ensemble_surface_provider import StatisticalSurfaceAddress

LOGGER = logging.getLogger(__name__)

# For some obscure reason, reading of a non-existent irap file segfaults,
# so use asymmetric file formats for read and write
FILE_FORMAT_WRITE = "irap_binary"
FILE_FORMAT_READ = "guess"
FILE_EXTENSION = ".gri"

# FILE_FORMAT_WRITE = "xtgregsurf"
# FILE_FORMAT_READ = FILE_FORMAT_WRITE
# FILE_EXTENSION = ".xtgregsurf"


class StatSurfCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        placeholder_file = self.cache_dir / "placeholder.txt"
        placeholder_file.write_text(
            f"Placeholder -- {datetime.datetime.now()} -- {os.getpid()}"
        )

    def fetch(
        self, address: StatisticalSurfaceAddress
    ) -> Optional[xtgeo.RegularSurface]:

        full_surf_path = self.cache_dir / _compose_stat_surf_file_name(
            address, FILE_EXTENSION
        )

        try:
            surf = xtgeo.surface_from_file(full_surf_path, fformat=FILE_FORMAT_READ)
            return surf
        # pylint: disable=bare-except
        except:
            return None

    def store(
        self, address: StatisticalSurfaceAddress, surface: xtgeo.RegularSurface
    ) -> None:

        surf_fn = _compose_stat_surf_file_name(address, FILE_EXTENSION)
        full_surf_path = self.cache_dir / surf_fn

        # Try and go via a temporary file which we don't rename until writing is finished.
        # to make the cache writing more concurrency-friendly.
        # One problem here is that we don't control the file handle (xtgeo does) so can't
        # enforce flush and sync of the file to disk before the rename :-(
        # Still, we probably need a more robust way of shring the cached surfaces...
        tmp_surf_path = self.cache_dir / (surf_fn + f"__{uuid.uuid4().hex}.tmp")
        try:
            surface.to_file(tmp_surf_path, fformat=FILE_FORMAT_WRITE)
            os.replace(tmp_surf_path, full_surf_path)
        # pylint: disable=bare-except
        except:
            os.remove(tmp_surf_path)

        # surface.to_file(full_surf_path, fformat=FILE_FORMAT_WRITE)


def _compose_stat_surf_file_name(
    address: StatisticalSurfaceAddress, extension: str
) -> str:

    # Should probably sort the realization list
    # Also, what about duplicates
    # And further, handling of missing realizations...

    pickled = pickle.dumps(address.realizations, pickle.HIGHEST_PROTOCOL)
    real_hash = hashlib.md5(pickled).hexdigest()  # nosec
    return "--".join(
        [
            f"{address.statistic}",
            f"{address.name}",
            f"{address.attribute}",
            f"{address.datestr}",
            f"{real_hash}{extension}",
        ]
    )
