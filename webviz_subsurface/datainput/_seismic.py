import numpy as np
from webviz_config.common_cache import CACHE


# @CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_xline(cube, xline):
    idx = np.where(cube.xlines == xline)
    return cube.values[:, idx, :][:, 0, 0].T.copy()


# @CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_iline(cube, iline):
    idx = np.where(cube.ilines == iline)
    return cube.values[idx, :, :][0, 0, :].T.copy()
