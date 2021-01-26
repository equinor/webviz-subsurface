import numpy as np
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_surface(surface_path: str) -> RegularSurface:
    return RegularSurface(surface_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence: np.ndarray, surface: RegularSurface) -> np.ndarray:
    return surface.get_fence(fence)
