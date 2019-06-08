import os
import pandas as pd
import xtgeo
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore


@cache.memoize(timeout=cache.TIMEOUT)
def load_well(well_name):
    return xtgeo.well.Well(well_name)

@cache.memoize(timeout=cache.TIMEOUT)
def load_cube(cube_name):
    return xtgeo.cube.Cube(cube_name)


def load_surface(s_name, real_path, surface_cat):
    path = os.path.join(real_path, 'share/results/maps',)
    s_path = os.path.join(path, f'{s_name}--{surface_cat}.gri')
    try:
        return xtgeo.surface.RegularSurface(s_path)
    except IOError:
        raise IOError


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def surface_to_df(s_name, real_path, surface_cat) -> pd.DataFrame:
    s = load_surface(s_name, real_path, surface_cat)
    return pd.DataFrame.from_dict([{
        'ncol': s.ncol,
        'nrow': s.nrow,
        'xori': s.xori,
        'yori': s.yori,
        'xinc': s.xinc,
        'yinc': s.yinc,
        'rotation': s.rotation,
        'values': s.npvalues1d}])


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def well_to_df(well_name) -> pd.DataFrame:
    return load_well(well_name).dataframe


@cache.memoize(timeout=cache.TIMEOUT)
def get_wfence(well_name, extend=200, tvdmin=0) -> pd.DataFrame:
    df = well_to_df(well_name)
    keep = ("X_UTME", "Y_UTMN", "Z_TVDSS")
    for col in df.columns:
        if col not in keep:
            df.drop(labels=col, axis=1, inplace=True)
    df["POLY_ID"] = 1
    df["NAME"] = well_name
    poly = xtgeo.Polygons()
    poly.dataframe = df
    poly.name = well_name

    if tvdmin is not None:
        poly.dataframe = poly.dataframe[poly.dataframe[poly.zname] >= tvdmin]
    data = poly.get_fence(extend=extend, asnumpy=True)
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str)
    return df


@cache.memoize(timeout=cache.TIMEOUT)
def get_cfence(well, cube_name):
    cube = load_cube(cube_name)
    return cube.get_randomline(get_wfence(well).values.copy())

@cache.memoize(timeout=cache.TIMEOUT)
def get_hfence(well, s_name, real_path, surface_cat) -> pd.DataFrame:
    df = surface_to_df(s_name, real_path, surface_cat)
    s = xtgeo.surface.RegularSurface(**df.to_dict('records')[0])
    fence = s.get_fence(get_wfence(well).values.copy())
    arr = fence[:, 2].copy().tolist()
    # print(fence)
    return pd.DataFrame(arr, columns=['fence'])
