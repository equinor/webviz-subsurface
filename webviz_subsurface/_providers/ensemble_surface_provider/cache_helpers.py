from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import flask_caching

from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO


@dataclass(frozen=False)
class _CacheInfo:
    root_cache_folder: Optional[Path]
    main_cache: Optional[flask_caching.SimpleCache]
    named_cache_dict: Dict[str, flask_caching.SimpleCache]


_CACHE_INFO: _CacheInfo = _CacheInfo(None, None, {})


def get_root_cache_folder() -> Path:
    if not _CACHE_INFO.root_cache_folder:
        _CACHE_INFO.root_cache_folder = (
            WEBVIZ_INSTANCE_INFO.storage_folder / "root_cache_folder"
        )

    return _CACHE_INFO.root_cache_folder


def get_or_create_cache() -> flask_caching.SimpleCache:
    if not _CACHE_INFO.main_cache:
        _CACHE_INFO.main_cache = _create_file_system_cache("_FlaskFileSystemCache_main")
        # _CACHE_INFO.main_cache = _create_redis_cache("main:")

    return _CACHE_INFO.main_cache


def get_or_create_named_cache(cache_name: str) -> flask_caching.SimpleCache:
    cache = _CACHE_INFO.named_cache_dict.get(cache_name)
    if cache is None:
        cache = _create_file_system_cache(f"_FlaskFileSystemCache__{cache_name}")
        # cache = _create_redis_cache(f"_{cache_name}:")
        _CACHE_INFO.named_cache_dict[cache_name] = cache

    return cache


def _create_file_system_cache(cache_sub_dir: str) -> flask_caching.SimpleCache:
    # Threshold is the maximum number of items the cache before it starts deleting some
    # of the items. A threshold value of 0 indicates no threshold.
    # The default timeout in seconds that is used, 0 indicates that the cache never expires

    # Note that NO deletion of cached items will ever be done before the item threshold
    # is reached regardless of the timeout specified.
    # Given that, what would a sensible item threshold be?
    # In cachelib, the default is 500. This seems a bit low, but setting the value too
    # high probably impacts performance since the file cache will regularly iterate over
    # all the files in the directory.

    item_threshold = 10000
    default_timeout_s = 3600

    flask_cache_dir = get_root_cache_folder() / cache_sub_dir

    return flask_caching.backends.FileSystemCache(
        cache_dir=flask_cache_dir,
        threshold=item_threshold,
        default_timeout=default_timeout_s,
    )


def _create_redis_cache(key_prefix: str) -> flask_caching.SimpleCache:

    default_timeout_s = 3600

    return flask_caching.backends.RedisCache(
        host="localhost",
        port=6379,
        default_timeout=default_timeout_s,
        key_prefix=key_prefix,
    )
