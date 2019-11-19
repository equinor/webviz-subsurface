import numpy as np

from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    return [x, y, z]

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence, surface):
    return surface.get_fence(fence)