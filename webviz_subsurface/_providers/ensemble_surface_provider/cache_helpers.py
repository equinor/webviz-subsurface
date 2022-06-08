from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import flask_caching

from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO


@dataclass(frozen=False)
class _CacheInfo:
    root_cache_folder: Optional[Path]
    main_cache: Optional[flask_caching.SimpleCache]


_CACHE_INFO: _CacheInfo = _CacheInfo(None, None)


def get_root_cache_folder() -> Path:
    if not _CACHE_INFO.root_cache_folder:
        _CACHE_INFO.root_cache_folder = (
            WEBVIZ_INSTANCE_INFO.storage_folder / "root_cache_folder"
        )

    return _CACHE_INFO.root_cache_folder


def get_or_create_cache() -> flask_caching.SimpleCache:
    if not _CACHE_INFO.main_cache:
        flask_cache_dir = get_root_cache_folder() / "_FileSystemCache"
        _CACHE_INFO.main_cache = flask_caching.backends.FileSystemCache(flask_cache_dir)

    return _CACHE_INFO.main_cache
