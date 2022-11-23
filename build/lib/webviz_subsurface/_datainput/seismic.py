import numpy as np
import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_cube_data(cube_path: str) -> xtgeo.Cube:
    return xtgeo.cube_from_file(cube_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_xline(cube: xtgeo.Cube, xline: int) -> np.ndarray:
    idx = np.where(cube.xlines == xline)
    return cube.values[:, idx, :][:, 0, 0].T


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_iline(cube: xtgeo.Cube, iline: int) -> np.ndarray:
    idx = np.where(cube.ilines == iline)
    return cube.values[idx, :, :][0, 0, :].T


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_zslice(cube: xtgeo.Cube, zslice: float) -> np.ndarray:
    idx = np.where(cube.zslices == zslice)
    return cube.values[:, :, idx][:, :, 0, 0].T
