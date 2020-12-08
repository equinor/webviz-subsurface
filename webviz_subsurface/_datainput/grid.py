from typing import Optional

import xtgeo
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_grid(gridpath: str) -> xtgeo.Grid:
    return xtgeo.grid_from_file(gridpath)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_grid_parameter(
    grid: Optional[xtgeo.Grid], gridparameterpath: str
) -> xtgeo.GridProperty:
    return xtgeo.gridproperty_from_file(gridparameterpath, grid=grid)
