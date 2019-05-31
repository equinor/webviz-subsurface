import os
import pandas as pd
try:
    import xtgeo
except ImportError:
    pass
from webviz_config.common_cache import cache


@cache.memoize(timeout=cache.TIMEOUT)
def load_well(well_name):
    return xtgeo.well.Well(well_name)


def load_surface(s_name, real_path, surface_cat):
    path = os.path.join(real_path, 'share/results/maps',)
    s_path = os.path.join(path, f'{s_name}--{surface_cat}.gri')
    try:
        return xtgeo.surface.RegularSurface(s_path)
    except IOError:
        raise IOError


@cache.memoize(timeout=cache.TIMEOUT)
def get_wfence(well_name, extend=200, tvdmin=0):
    well = load_well(well_name)
    data = well.get_fence_polyline(sampling=20, extend=extend, tvdmin=tvdmin)
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str)
    return df


@cache.memoize(timeout=cache.TIMEOUT)
def get_hfence(well, surface):
    return surface.get_fence(get_wfence(well).values.copy())
