import numpy as np
import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize()
def load_surface(surface_path: str) -> xtgeo.RegularSurface:
    return xtgeo.surface_from_file(surface_path)


@CACHE.memoize()
def get_surface_fence(fence: np.ndarray, surface: xtgeo.RegularSurface) -> np.ndarray:
    return surface.get_fence(fence)
