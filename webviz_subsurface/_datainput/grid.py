import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_grid(gridpath):
    return xtgeo.grid_from_file(gridpath)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_grid_parameter(grid, gridparameterpath):
    return xtgeo.gridproperty_from_file(gridparameterpath, grid=grid)
