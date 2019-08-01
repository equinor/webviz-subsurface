import os
from glob import glob
from pathlib import PurePath
import pandas as pd
import xtgeo
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
from ._history_match import scratch_ensemble


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
    '''Convert Irap Bin surface to Pandas dataframe'''
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
def get_wfence(well_name, nextend=200, tvdmin=0) -> pd.DataFrame:
    '''Generate 2D array along well path'''
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
    data = poly.get_fence(nextend=nextend, asnumpy=True)
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str)
    return df


@cache.memoize(timeout=cache.TIMEOUT)
def get_cfence(well, cube_name):
    '''Slice cube along well fence'''
    cube = load_cube(cube_name)
    return cube.get_randomline(get_wfence(well).values.copy())


@cache.memoize(timeout=cache.TIMEOUT)
def load_grid(g_name):
    return xtgeo.grid3d.Grid(g_name)


@cache.memoize(timeout=cache.TIMEOUT)
def load_parameter(p_name):
    return xtgeo.grid3d.GridProperty().from_file(p_name, fformat="roff")


@cache.memoize(timeout=cache.TIMEOUT)
def get_gfence(well, g_name, p_name):
    '''Slice cube along well fence'''
    try:
        grid = load_grid(g_name)
        parameter = load_parameter(p_name)

        return grid.get_randomline(
            get_wfence(well).values.copy(), parameter,
            zmin=1500, zmax=1900, zincrement=1.0)
    except IOError:
        return


@cache.memoize(timeout=cache.TIMEOUT)
def get_hfence(well, s_name, real_path, surface_cat) -> pd.DataFrame:
    '''Slice surface along well fence'''
    df = surface_to_df(s_name, real_path, surface_cat)
    s = xtgeo.surface.RegularSurface(**df.to_dict('records')[0])
    fence = s.get_fence(get_wfence(well).values.copy())
    arr = fence[:, 2].copy().tolist()
    return pd.DataFrame(arr, columns=['fence'])


@cache.memoize(timeout=cache.TIMEOUT)
def make_well_trace(well, tvdmin=0):
    '''Creates well trace for graph'''
    x = [trace[3]
         for trace in get_wfence(well, nextend=2, tvdmin=tvdmin).values]
    y = [trace[2]
         for trace in get_wfence(well, nextend=2, tvdmin=tvdmin).values]
    # Filter out elements less than tvdmin
    # https://stackoverflow.com/questions/17995302/filtering-two-lists-simultaneously
    try:
        y, x = zip(*((y_el, x) for y_el, x in zip(y, x) if y_el >= tvdmin))
    except ValueError:
        pass
    x = x[1:-1]
    y = y[1:-1]
    return {
        'x': x,
        'y': y,
        'name': PurePath(well).stem,
        'fill': None,
        'mode': 'lines',
        'marker': {'color': 'black'}
    }


@cache.memoize(timeout=cache.TIMEOUT)
def make_surface_traces(well, reals, surf_name, cat, color):
    '''Creates surface traces for graph'''
    plot_data = []
    x = [trace[3] for trace in get_wfence(well, nextend=200, tvdmin=0).values]
    for j, real in enumerate(reals):
        y = get_hfence(well, surf_name, real, cat)['fence']
        showlegend = True if j == 0 else False
        plot_data.append(
            {
                'x': x,
                'y': y,
                'name': surf_name,
                'hoverinfo': 'none',
                'legendgroup': surf_name,
                'showlegend': showlegend,
                'real': real,
                'marker': {'color': color}
            })
    return pd.DataFrame(plot_data)


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def make_param_trace(well, grid, parameter) -> pd.DataFrame:

    try:
        hmin, hmax, vmin, vmax, values = get_gfence(well, grid, parameter)
    except TypeError:
        return pd.DataFrame([{
            'x0': 0,
            'xmax': 0,
            'dx': 0,
            'y0': 0,
            'ymax': 0,
            'dy': 0,
            'type': 'heatmap',
            'z':  [[]]}])
    x_inc = (hmax-hmin)/values.shape[1]
    y_inc = (vmax-vmin)/values.shape[0]
    return pd.DataFrame([{
        'type': 'heatmap',
        'z': values.tolist(),
        'x0': hmin,
        'xmax': hmax,
        'dx': x_inc,
        'y0': vmin,
        'ymax': vmax,
        'dy': y_inc,
        'zsmooth': 'best'
    }])


@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def make_cube_trace(well, cube) -> pd.DataFrame:
    hmin, hmax, vmin, vmax, values = get_cfence(well, cube)
    x_inc = (hmax-hmin)/values.shape[1]
    y_inc = (vmax-vmin)/values.shape[0]
    return pd.DataFrame([{
        'type': 'heatmap',
        'z': values.tolist(),
        'x0': hmin,
        'xmax': hmax,
        'dx': x_inc,
        'y0': vmin,
        'ymax': vmax,
        'dy': y_inc,
        'zsmooth': 'best'
    }])


@webvizstore
def get_realizations(ens, ens_path) -> pd.DataFrame:
    ensemble = scratch_ensemble(ens, ens_path)
    paths = [ensemble._realizations[real]._origpath
             for real in ensemble._realizations]
    reals = [real for real in ensemble._realizations]
    return pd.DataFrame({'REAL': reals, 'PATH': paths})\
        .sort_values(by=['REAL'])


@webvizstore
def get_file_paths(folder, suffix) -> pd.DataFrame:
    glob_pattern = f'{folder}/*{suffix}'
    files = sorted([f for f in glob(glob_pattern)])
    return pd.DataFrame({'PATH': files})
